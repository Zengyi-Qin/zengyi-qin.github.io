### [www.qinzy.tech](www.qinzy.tech)

## Editing the site

Edit the focused files in `src/` rather than the generated `index.html`:

- `src/templates/head.html` — metadata and the stylesheet link
- `src/sections/` — profile, bio, news, and publication groups (loaded in filename order)
- `assets/site.css` — all visual styling

After an edit, run:

```sh
python3 build.py
```

Commit both your source edit and the regenerated `index.html`. GitHub Pages only serves
the latter, so it needs no build configuration.
