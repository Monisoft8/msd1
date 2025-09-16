from msd import create_app

app = create_app()

if __name__ == "__main__":
    # يمكنك تغيير debug/host/port حسب حاجتك
    app.run(host="0.0.0.0", port=5000, debug=True)
