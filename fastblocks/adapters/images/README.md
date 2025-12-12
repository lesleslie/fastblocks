# Image Adapters

> **FastBlocks Documentation**: [Main](../../../README.md) | [Adapters](../README.md) | [Templates](../templates/README.md)
>
> _Last reviewed: 2025-11-19_

Image adapters wrap third-party media services so FastBlocks can upload, transform, and embed assets from a unified interface (`ImagesBase`/`ImagesProtocol`). Adapters register themselves under the `"images"` dependency key which keeps template filters and background jobs decoupled from vendor specifics.

## Available Implementations

| Adapter | Module | Highlights |
|---------|--------|------------|
| Cloudinary | `cloudinary.py` | Full upload + transformation pipeline using Cloudinary's API and delivery CDN. |
| ImageKit | `imagekit.py` | Real-time transformation URLs with signed requests and media library helpers. |
| Cloudflare Images | `cloudflare.py` | Fetch tokens and generate optimized delivery URLs for Cloudflare's image storage. |
| TwicPics | `twicpics.py` | Responsive, focus-aware cropping via TwicPics' smart transformation service. |

Each adapter inherits the common `ImagesBaseSettings`, so you always get CDN configuration, default transformations, and lazy-loading flags even when switching providers.

## Configuration

Example `settings/adapters/images.yml` targeting Cloudinary:

```yaml
images:
  adapter: cloudinary
  settings:
    cloud_name: "${CLOUDINARY_CLOUD_NAME}"
    api_key: "${CLOUDINARY_API_KEY}"
    api_secret: "${CLOUDINARY_API_SECRET}"
    default_transformations:
      quality: "auto"
      fetch_format: "auto"
```

Swap the `adapter` value to `imagekit`, `cloudflare`, or `twicpics` and supply the credentials required by that provider’s settings class.

## Template Helpers

`fastblocks/adapters/templates/_enhanced_filters.py` exposes convenience helpers that defer to the configured adapter whenever possible and fall back to static HTML otherwise:

- `[[ cf_image_url('hero.jpg', width=800, quality=85) ]]` – build Cloudflare Images URLs with transformation query strings.
- `[[ cf_responsive_image('hero.jpg', 'Hero', {'mobile': {'width': 400}}) | safe ]]` – output `<img>` tags with generated `srcset` values.
- `[[ twicpics_image('product.jpg', resize='400x300') ]]` / `[[ twicpics_smart_crop('id', 400, 250, 'face') | safe ]]` – leverage TwicPics' smart cropping modes.

Adapters that implement `get_img_tag()` can also be called directly inside your application code for fine-grained control.

## Extending

When building a new adapter:

1. Subclass `ImagesBaseSettings` for configuration (API keys, delivery domains, etc.).
1. Implement an `ImagesBase` subclass with `upload_image()`, `get_image_url()`, and `get_img_tag()`.
1. Register any extra template filters if your service exposes unique capabilities (e.g., custom transformation macros).

See the Cloudinary and ImageKit modules for realistic end-to-end implementations.
