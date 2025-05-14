from flask import Flask, render_template, jsonify
import pandas as pd
from flask_cors import CORS
from waitress import serve


app = Flask(__name__)
CORS(app)

# Function to read CSV file
def read_csv(path):
    try:
       
        df = pd.read_csv(path)
        return df
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return pd.DataFrame()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/page1')
def page1():
    return render_template("page1.html")

@app.route('/page2')
def page2():
    return render_template("page2.html")

@app.route('/api/data1', methods=['GET'])
def get_csv_data1():
    df = read_csv('k_output.csv')
    if df.empty:
        return jsonify({"error": "No data available"})
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/data2', methods=['GET'])
def get_csv_data():
    df = read_csv('srk_output.csv')
    if df.empty:
        return jsonify({"error": "No data available"})
    return jsonify(df.to_dict(orient='records'))

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000)

    