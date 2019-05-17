import os
import config
from konbini.app import create_app

if hasattr(config, 'TEMPLATE_FOLDER'):
    app = create_app(
        static_folder=os.path.join(config.TEMPLATE_FOLDER, 'static'),
        template_folder=config.TEMPLATE_FOLDER)
else:
    app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
