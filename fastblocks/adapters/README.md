# FastBlocks Adapters

This directory contains protocol-based adapters for FastBlocks that follow best practices for ACB, FastBlocks, and Crackerjack. These adapters inject the correct HTML tags, CSS styles, or other head metadata into templates depending on the configured adapter module.

## Adapter Categories

### Images

Manage image optimization, transformation, and delivery through various services:

- Cloudinary
- ImageKit
- Cloudflare Images
- TwicPics
- Standard HTML img tags

### Styles

Provide CSS frameworks and styling solutions:

- Bulma
- Vanilla CSS
- WebAwesome
- KelpUI

### Icons

Offer icon libraries for UI components:

- FontAwesome
- Lucide
- Phosphor
- Heroicons
- Remix
- Material Icons

### Fonts

Handle web font integration and management:

- Google Fonts
- Font Squirrel (self-hosted)
- FontSpace (manual)

## Architecture

All adapters follow the ACB adapter pattern with:

- Base interface definitions in `_base.py`
- Module implementations in `{module_name}.py`
- Configuration-driven selection
- Protocol-based type safety
- Template integration through custom Jinja2 filters

## Configuration

Each adapter category has its own configuration file in the `settings/` directory:

- `settings/images.yml`
- `settings/styles.yml`
- `settings/icons.yml`
- `settings/fonts.yml`

## Documentation

For detailed implementation plans, see:

- `ADAPTER_IMPLEMENTATION_PLAN.md` - Technical implementation details
- `ADAPTER_MODULE_SELECTION.md` - Rationale for module selection

## Usage

Adapters are automatically initialized based on configuration and can be accessed through FastBlocks' dependency injection system.
