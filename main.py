from config import setup_page_config
from ui_components import loadUiComponents

def main():
    """Main entry point for the Streamlit dashboard"""
    setup_page_config()
    loadUiComponents()

if __name__ == "__main__":
    main()
