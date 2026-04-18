from flask import Blueprint, request, jsonify
from utils.security import check_password
from Database.db import get_db_connection
from flask_jwt_extended import create_access_token