import os
import flask

app = flask.Flask(__name__)

@app.route('/')
def hello():
    return '你好 GAE！我的第一个 Python 应用！'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)