# Craft: color

Color carries least information, attracts most attention. Design interface
in grayscale first; color, gradients included, cannot fix hierarchy that
does not already read.

## Structure

* **One accent.** Single color means action, selection, focus, and holds
  across every screen; never one for buttons, another for links, a third for
  charts. System supplied: one *declared* accent honored exactly; declared
  accent plus reserved secondary hues is consistent when used as declared,
  inconsistent the moment component invents another value.
* **One neutral family**, consistently warm or cool. Users perceive mixed
  warm and cool greys as mismatch even when they cannot name it.
* **Semantic colors** for success, warning, danger, information, each
  distinguishable from accent and each other, so alerts read as alerts.
  Danger must never be accent, or destructive actions stop reading as
  destructive.
* Restrained saturation for large areas; full saturation only for small,
  deliberate emphasis. Saturated field fatigues; saturated twelve-pixel dot
  informs.

## Tokens, not values

Name by role. Token `surface-raised` survives theme change; `grey-100`
becomes wrong when theme inverts. Roles worth having: page and raised
surfaces; primary, secondary, disabled text; subtle and strong borders;
accent plus its hover, active, subtle variants; semantic set; focus ring.

Author in perceptually uniform color space where toolchain supports it, so
lightness step means same visual change at every hue. Derive hover and
active states by adjusting lightness within space; let platform's color
mixing do derivation so relationship survives token change.

## Both themes, from the start

Design light and dark together. Retrofitted theme produces one designed mode
and one inverted mode.

* Near-black and near-white for large surfaces. Pure black kills depth and
  smears on some displays; pure white glares.
* Dark mode is not inversion. Elevation reverses: raised surfaces get
  lighter, shadows do less work, so borders and surface lightness carry
  elevation.
* Saturated colors vibrate against dark backgrounds. Reduce saturation,
  raise lightness for accents in dark mode.
* Hierarchy parity required: whatever draws eye first in light draws it
  first in dark.
* Select between theme values through platform's own single-declaration
  mechanism, so interface tracks operating system preference live.
* **Default to system preference; store nothing.** Ship no
  `light | dark | system` setting, no persisted choice, no app-level theme
  state unless user asks for toggle.
* Add toggle when user asks, or when mode loses meaningful brand expression.
  Default it to system preference; persist choice per `interaction`.

## Contrast in practice

`a11y` owns thresholds, exemptions, their interpretation. Compute every
ratio; estimates and supplied document's claims are unverified.

* Style placeholder, helper, disabled-looking, secondary text to read as
  secondary, then measure each against every surface it appears on,
  including tinted cards. Grey text lightened until it looks refined usually
  fails.
* Accent failing at body size often passes at display size: decide where
  brand color may carry text before committing it to button.
* Text over imagery needs guaranteed backing: scrim, gradient, or solid
  panel. Contrast against image's average color is not contrast against
  pixels behind letters.
* Color never the only channel. Pair with text, icon, weight, or position.
* Keep forced-colors and high-contrast modes functional.

## Choosing a palette

Let brand, domain, audience choose. Nothing constrains choice: avoid
reflexive families of generated design: purple-to-blue technology gradient;
warm cream with brass and oxblood on every artisan and premium consumer
brief. Both make distinct brands look identical.

Choose direction coherent and unusual for category: saturated single hue
against one neutral, deep natural tone with warm accent, sharp near-black
against warm mid-tone, or true monochrome with one bright accent. Rotate
across projects; same palette twice within category means palette came from
habit.
