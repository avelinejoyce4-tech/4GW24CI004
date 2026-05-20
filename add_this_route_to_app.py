# ─────────────────────────────────────────────────────────────
# ADD THIS ROUTE to your app.py (paste anywhere above the last
# `if __name__ == '__main__':` line)
# ─────────────────────────────────────────────────────────────

@app.route('/audio-upload')
def audio_upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('audio_upload.html')
