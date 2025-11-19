______________________________________________________________________

## id: 01K6JZ5DW0CP081YBXFFP3QFMV

______________________________________________________________________

## id: 01K6J6B52AHGK3YMJEB390GYF8

______________________________________________________________________

## id: 01K6HPXYC8YRRQ6XT49RXP0B24

______________________________________________________________________

## id: 01K6HPWXWGSJCN0HKRRGHDN21D

______________________________________________________________________

## id: 01K6HPNPZ7CA9SG8FQD8SJ2S7N

______________________________________________________________________

## id: 01K6HPKY2X5XK5KVXVRV6CPAXC

______________________________________________________________________

## id: 01K6H6RMTY9KF87BXB5Y2E8E0Y

______________________________________________________________________

## id: 01K6H6HJVXJ4GTRVNHXYDYK09H

______________________________________________________________________

## id: 01K6H6G86SQPYEWXXAR1ZJVXRV

______________________________________________________________________

## id: 01K6H6FA5DRRMDBA6FA0FC9M2C

______________________________________________________________________

## id: 01K6H5NVH2TV3NA8E29WMM5DYN

______________________________________________________________________

## id: 01K6H57CE95KBNDXKKK2SNPXPW

______________________________________________________________________

## id: 01K6H0YJMX2E46K09RXDBD5ZAS

______________________________________________________________________

## id: 01K6GZPG5SYT10D8GEK7483DPN

______________________________________________________________________

## id: 01K6GZMEVJ9XCPPMGKP86KWN5H

______________________________________________________________________

## id: 01K6GZHB7XBFF1EFRKJMVYXSQ2

______________________________________________________________________

## id: 01K6GZFQAKM7TN0AETQ4K6DX57

______________________________________________________________________

## id: 01K6GYFF46E4ZDJMKJ0KQ2V5FR

______________________________________________________________________

## id: 01K6GYEVSYYZ2N9FM6PT6EPRZF

______________________________________________________________________

## id: 01K6GXNRX112WBNBM9SS3YZ4V0

______________________________________________________________________

## id: 01K6GXN5BY4R6Y71JQ41WRM8NG

______________________________________________________________________

## id: 01K6GXHT63HWH9JX9WNN487KGG

______________________________________________________________________

## id: 01K6GX8ZV999NG5SQDGKJTSJZS

# FastBlocks Template Examples

This guide provides comprehensive examples of using FastBlocks adapter filters in Jinja2 templates with both sync and async patterns.

## Basic Image Integration

```jinja2
[% extends "base.html" %]

[% block content %]
<div class="hero-section">
    <!-- Basic image tag with adapter integration -->
    [[ img_tag('hero-banner.jpg', 'Welcome Banner', class='hero-image', width=1200) ]]

    <!-- Async image with transformations -->
    [[ await async_image_with_transformations('hero-banner.jpg', 'Welcome Banner',
                                             {'width': 1200, 'quality': 85, 'format': 'webp'},
                                             class='hero-image', loading='eager') ]]
</div>
[% endblock %]
```

## Responsive Image Integration

```jinja2
[% extends "base.html" %]

[% block content %]
<article class="blog-post">
    <h1>Article Title</h1>

    <!-- Responsive image with multiple sizes -->
    [[ await async_responsive_image('article-hero.jpg', 'Article Hero Image', {
        'mobile': {'width': 400, 'quality': 75, 'format': 'webp'},
        'tablet': {'width': 800, 'quality': 80, 'format': 'webp'},
        'desktop': {'width': 1200, 'quality': 85, 'format': 'webp'}
    }, class='article-hero', loading='lazy') ]]

    <div class="article-content">
        <!-- Lazy loading image -->
        [[ await async_lazy_image('content-image.jpg', 'Content Image',
                                  width=600, height=400, class='content-img') ]]
    </div>
</article>
[% endblock %]
```

## Icon Integration

```jinja2
[% extends "base.html" %]

[% block content %]
<nav class="user-nav">
    <!-- Phosphor icon with custom size and variant -->
    [[ ph_icon("user-circle", variant="fill", size="lg") | safe ]]

    <!-- Interactive icon with action -->
    [[ ph_interactive("sign-out", action="logout()") | safe ]]

    <!-- Heroicons integration -->
    [[ heroicon("user", variant="outline", size="6") | safe ]]
</nav>
[% endblock %]
```

## Font Loading with Optimization

```jinja2
<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Enhanced font loading with optimization -->
    [[ await async_optimized_font_loading(['Inter', 'Roboto Mono'], critical=True) ]]

    <style>
        [[ font_face_declaration('CustomFont', {
            'woff2': '/fonts/custom.woff2',
            'woff': '/fonts/custom.woff'
        }, weight='400', style='normal') ]]

        body {
            font-family: [[ font_family('primary') ]];
        }
    </style>
</head>
</html>
```

## HTMX Integration

```jinja2
<div class="htmx-container">
    <!-- HTMX-powered content loading -->
    <button
        hx-get="/api/data"
        hx-target="#result"
        hx-swap="innerHTML"
        class="btn">
        Load Data
    </button>

    <div id="result">
        [# Content will be loaded here #]
    </div>
</div>
```

## Style Framework Integration

```jinja2
[% extends "base.html" %]

[% block content %]
<div class="container">
    <!-- Stylesheet links from all adapters -->
    [[ stylesheet_links() ]]

    <!-- Framework-specific utilities -->
    <div class="[[  grid_class('cols', 3) ]]">
        <div class="[[ utility_class('card') ]]">
            Card 1
        </div>
        <div class="[[ utility_class('card') ]]">
            Card 2
        </div>
        <div class="[[ utility_class('card') ]]">
            Card 3
        </div>
    </div>
</div>
[% endblock %]
```

## Fragment Templates for HTMX

```jinja2
[# Fragment template for partial page updates #]
[% block user_profile %]
<div class="user-profile" id="profile-[[ user.id ]]">
    <div class="avatar">
        [[ img_tag(user.avatar_url, user.name, class='avatar-img') ]]
    </div>
    <div class="details">
        <h3>[[ user.name ]]</h3>
        <p>[[ user.email ]]</p>
        <p class="bio">[[ user.bio | default('No bio provided') ]]</p>
    </div>
</div>
[% endblock %]
```

## Advanced Validation Example

```jinja2
<!DOCTYPE html>
<html lang="en">
<head>
    <title>[[ title | default('FastBlocks App') ]]</title>
</head>
<body>
    [% if user %]
        <nav class="user-nav">
            [[ ph_icon("user-circle", variant="fill", size="lg") | safe ]]
            <span>[[ user.email ]]</span>
            [[ ph_interactive("sign-out", action="logout()") | safe ]]
        </nav>
    [% else %]
        <div class="guest-banner">
            <p>Welcome, Guest!</p>
            <a href="/login">Sign In</a>
        </div>
    [% endif %]

    [% block content %]
    [# Main content here #]
    [% endblock %]
</body>
</html>
```

## Performance Optimization Patterns

```jinja2
[# 1. Use async filters for I/O operations #]
[[ await async_image_with_transformations('banner.jpg', 'Banner',
                                         {'width': 1200, 'format': 'webp'}) ]]

[# 2. Lazy load non-critical images #]
[[ await async_lazy_image('footer-logo.png', 'Logo',
                          loading='lazy', class='footer-logo') ]]

[# 3. Preload critical fonts #]
[[ await async_optimized_font_loading(['Inter'], critical=True) ]]

[# 4. Use fragment templates for HTMX updates #]
[% include "fragments/user_card.html" %]
```

## Complete Example: Blog Post Page

```jinja2
[% extends "base.html" %]

[% block title %][[ post.title ]] - Blog[% endblock %]

[% block head %]
    [# Critical font loading #]
    [[ await async_optimized_font_loading(['Merriweather', 'Open Sans'], critical=True) ]]

    [# Stylesheet links #]
    [[ stylesheet_links() ]]
[% endblock %]

[% block content %]
<article class="blog-post">
    <header class="post-header">
        <h1>[[ post.title ]]</h1>

        <div class="post-meta">
            <div class="author">
                [[ ph_icon("user", variant="fill") | safe ]]
                <span>[[ post.author.name ]]</span>
            </div>

            <div class="date">
                [[ ph_icon("calendar", variant="regular") | safe ]]
                <time datetime="[[ post.created_at ]]">
                    [[ post.created_at | date_format('%B %d, %Y') ]]
                </time>
            </div>
        </div>

        [# Hero image with responsive variants #]
        [[ await async_responsive_image(post.hero_image, post.title, {
            'mobile': {'width': 400, 'quality': 75},
            'tablet': {'width': 800, 'quality': 80},
            'desktop': {'width': 1200, 'quality': 85}
        }, class='post-hero', loading='eager') ]]
    </header>

    <div class="post-content">
        [[ post.content | safe ]]
    </div>

    <footer class="post-footer">
        <div class="tags">
            [% for tag in post.tags %]
                <span class="tag">[[ tag ]]</span>
            [% endfor %]
        </div>

        <div class="share-buttons">
            [[ ph_interactive("share", action="sharePost('[[ post.id ]]')") | safe ]]
        </div>
    </footer>
</article>

[# Related posts loaded via HTMX #]
<section
    class="related-posts"
    hx-get="/api/posts/[[ post.id ]]/related"
    hx-trigger="load"
    hx-swap="innerHTML">
    <div class="loading">
        Loading related posts...
    </div>
</section>
[% endblock %]
```

## See Also

- [Adapter Documentation](../../fastblocks/adapters/README.md)
- [Syntax Demo Script](./syntax_demo.py) - Interactive demonstration of FastBlocks syntax support
