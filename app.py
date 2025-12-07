"""Entry point that exposes the Flask app created in asr_tool."""

from asr_tool import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
