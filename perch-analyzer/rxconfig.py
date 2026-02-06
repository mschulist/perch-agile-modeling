import reflex as rx


config = rx.Config(
    app_name="Perch_Analyzer",
    app_module_import="perch_analyzer.gui.index",
    # Serve the data directory as static files
    # This allows the browser to access spectrograms and audio files
    backend_port=8000,
    frontend_port=3000,
    plugins=[rx.plugins.sitemap.SitemapPlugin()],
)
