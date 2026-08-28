"""
app.py

Steganographic Exfil Simulator - hides encrypted data inside images (the
red team side) and detects when that's been done (the blue team side).

Three flows, three routes:
  /api/conceal  - encrypt a message, hide it in an uploaded image, return
                  the resulting PNG for download
  /api/detect   - scan an uploaded image, return a suspicion verdict plus
                  a visual of its hidden bit-plane
  /api/reveal   - given a stego image and the right password, recover the
                  original message (proves the round trip actually works)
"""

import io
import base64

from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image

import stego
import crypto_utils
import detector

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB upload cap


def _image_to_base64(img) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/conceal", methods=["POST"])
def api_conceal():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded."}), 400

    message = request.form.get("message", "").strip()
    password = request.form.get("password", "")
    if not message or not password:
        return jsonify({"error": "Both a message and a password are required."}), 400

    try:
        image = Image.open(request.files["image"].stream)
    except Exception:
        return jsonify({"error": "That doesn't look like a valid image file."}), 400

    encrypted = crypto_utils.encrypt_message(message, password)

    try:
        stego_img = stego.embed_data(image, encrypted)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    buf = io.BytesIO()
    stego_img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=True, download_name="concealed.png")


@app.route("/api/detect", methods=["POST"])
def api_detect():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded."}), 400

    try:
        image = Image.open(request.files["image"].stream)
    except Exception:
        return jsonify({"error": "That doesn't look like a valid image file."}), 400

    result = detector.scan_image(image)
    lsb_plane = detector.extract_lsb_plane(image)
    result["lsb_plane"] = _image_to_base64(lsb_plane)
    return jsonify(result)


@app.route("/api/reveal", methods=["POST"])
def api_reveal():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded."}), 400

    password = request.form.get("password", "")
    if not password:
        return jsonify({"error": "A password is required."}), 400

    try:
        image = Image.open(request.files["image"].stream)
    except Exception:
        return jsonify({"error": "That doesn't look like a valid image file."}), 400

    payload = stego.extract_data(image)
    if payload is None:
        return jsonify({"error": "No hidden data found in this image."}), 404

    try:
        message = crypto_utils.decrypt_message(payload, password)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": message})


if __name__ == "__main__":
    app.run(debug=True, port=5002)
