import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "adapters.app.main:app",
        reload=True,
        reload_includes=["*.py"],
        reload_excludes=["tmp/*", "settings/*", "theme/*"],
    )
