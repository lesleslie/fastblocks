import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_includes=["*.py"],
        reload_excludes=[
            "tmp/*",
            "settings/*",
            "templates/*",
        ],
    )
