import config
from shop import create_app

app = create_app(template_folder=config.TEMPLATE_FOLDER)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
