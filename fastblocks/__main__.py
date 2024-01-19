import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "fastblocks.adapters.app.main:app",
        reload=True,
        reload_excludes=["tmp/*", "settings/*", "theme/*"],
    )
