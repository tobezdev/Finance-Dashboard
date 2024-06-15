from app import app

if __name__ == "__main__":
    import gunicorn
    gunicorn.run("wsgi:app", workers=1)