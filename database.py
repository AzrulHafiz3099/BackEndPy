import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="db_gradingbot"
        )
        return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None
