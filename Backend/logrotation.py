from flask import Flask, jsonify
from flask_cors import CORS
import re
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Chemin vers votre fichier de logs
LOG_FILE = r"C:\Users\HP\Downloads\NetWeb\Backend\notifier.log"
aggregated = {}

def parse_log_file():
    """Lit et agrège les logs"""
    global aggregated
    
    if not os.path.exists(LOG_FILE):
        print(f"⚠️ Fichier non trouvé: {LOG_FILE}")
        return
    
    print(f"📖 Lecture du fichier: {LOG_FILE}")
    new_aggregated = {}
    total_lines = 0
    
    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    for line in lines:
        # Chercher payload='{...}'
        match = re.search(r"payload='(\{.*?\})'", line)
        if not match:
            continue
        
        total_lines += 1
        try:
            json_str = match.group(1)
            json_str = re.sub(r'\s*:\s*', ':', json_str)
            data = json.loads(json_str)
            
            src = data.get('src', '0.0.0.0:0')
            src_ip = src.split(':')[0] if ':' in src else src
            src_port = src.split(':')[1] if ':' in src else '?'
            
            dst = data.get('dst', '0.0.0.0:0')
            dst_ip = dst.split(':')[0] if ':' in dst else dst
            dst_port = dst.split(':')[1] if ':' in dst else '?'
            
            name = data.get('name', 'Alerte inconnue')
            severity = data.get('severity', 'low').lower()
            proto = data.get('proto', 'TCP')
            alert_id = data.get('id', 0)
            
            ts_raw = data.get('timestamp', '')
            if ts_raw:
                timestamp = ts_raw.split('.')[0].split('+')[0]
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            key = f"{src_ip}|||{name}"
            
            if key in new_aggregated:
                new_aggregated[key]['count'] += 1
                new_aggregated[key]['last_seen'] = timestamp
                if alert_id and alert_id not in new_aggregated[key]['ids']:
                    new_aggregated[key]['ids'].append(alert_id)
            else:
                new_aggregated[key] = {
                    'name': name,
                    'severity': severity,
                    'src_ip': src_ip,
                    'src_port': src_port,
                    'dst_ip': dst_ip,
                    'dst_port': dst_port,
                    'proto': proto,
                    'count': 1,
                    'first_seen': timestamp,
                    'last_seen': timestamp,
                    'ids': [alert_id] if alert_id else []
                }
        except Exception as e:
            print(f"Erreur parsing: {e}")
    
    aggregated = new_aggregated
    print(f"✅ {total_lines} alertes trouvées → {len(aggregated)} signatures uniques")
    
    # Afficher quelques stats
    for key, value in list(aggregated.items())[:5]:
        print(f"   - {value['src_ip']}: {value['name']} ({value['count']} fois)")

@app.route('/api/logs')
def get_logs():
    """Retourne les logs agrégés"""
    parse_log_file()
    logs = list(aggregated.values())
    logs.sort(key=lambda x: x['last_seen'], reverse=True)
    
    total_raw = sum(l['count'] for l in logs)
    
    return jsonify({
        'success': True,
        'raw_count': total_raw,
        'aggregated_count': len(logs),
        'unique_ips': len(set(l['src_ip'] for l in logs)),
        'rate_per_minute': len(logs),
        'logs': logs
    })

@app.route('/api/reset', methods=['POST'])
def reset():
    global aggregated
    aggregated = {}
    return jsonify({'success': True})

@app.route('/api/status')
def status():
    return jsonify({
        'success': True,
        'file_exists': os.path.exists(LOG_FILE),
        'file_path': LOG_FILE,
        'aggregated_count': len(aggregated)
    })

if __name__ == '__main__':
    print("=" * 60)
    print("  🛡️  SNORT IDS - SERVEUR AUTOMATIQUE")
    print("=" * 60)
    print(f"  📁 Fichier surveillé: {LOG_FILE}")
    print(f"  🔗 API: http://localhost:5050/api/logs")
    print("=" * 60)
    print("  ✅ Démarrage du serveur...")
    print("  🚀 Ouvrez http://localhost:5051 pour l'interface")
    print("  ⚡ CTRL+C pour arrêter")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5050, debug=False)