import os
from flask import Flask
from flask_cors import CORS
from app.models.database import init_db
from app.routes.pricing import pricing_bp
from app.routes.discount import discount_bp
from app.routes.visualization import visualization_bp
from app.routes.price_analysis import price_analysis_bp
from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.forecast_integration import forecast_bp





#  Application Factory Function
def create_app():

    """Creates and configures the Flask application."""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    #  Load Configuration
    app.config.from_object('app.config.Config')

    #  Initialize MongoDB Connection
    try:
        init_db()
        print(" Database initialized successfully!")
    except Exception as e:
        print(f" Database initialization failed: {e}")
        raise

    #  Register Blueprints (API routes)
    app.register_blueprint(pricing_bp, url_prefix='/api/pricing')
    app.register_blueprint(discount_bp, url_prefix='/api/discount')
    app.register_blueprint(visualization_bp, url_prefix='/api/visualization')  
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(price_analysis_bp, url_prefix='/api/price-analysis')  #  NEW ROUTE
    app.register_blueprint(forecast_bp, url_prefix='/api/demand-forecasting')




    #  Health Check Route
    @app.route('/')
    def health_check():
        return {"status": "OK", "message": " Consult Your Data API is running!"}

    return app

#  Create Flask App Object
app = create_app()

if __name__ == "__main__":
    #  Run the Flask Application
    app.run(debug=True, host="0.0.0.0", port=5000)
