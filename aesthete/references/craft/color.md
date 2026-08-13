# Craft: color

Color carries the least information and attracts the most attention. Design
the interface in grayscale first; if the hierarchy does not read, color will
not save it.

## Structure

* **One accent.** A single color means action, selection, and focus. Once
  chosen, it holds across every screen. A second accent appearing in one
  section is the most common consistency failure and reads as a bug. Where a
  system is supplied, this means one *declared* accent honored exactly: a
  declared accent plus reserved secondary hues is consistent when used as
  declared, and inconsistent the moment a component invents another value.
* **One neutral family**, consistently warm or cool. Mixing warm and cool
  greys in one surface produces a subtle dirtiness nobody can name and
  everybody perceives.
* **Semantic colors** for success, warning, danger, and information, each
  distinguishable from the accent and from each other. Danger must never be
  the accent, or destructive actions stop reading as destructive.
* Keep saturation restrained for large areas and reserve full saturation for
  small, deliberate emphasis. A saturated field fatigues; a saturated
  twelve-pixel dot informs.

## Tokens, not values

Name by role, never by appearance. A token called `surface-raised` survives
a theme change; one called `grey-100` becomes a lie the moment the theme
inverts. Roles worth having: page and raised surfaces, primary, secondary,
and disabled text, subtle and strong borders, the accent plus its hover,
active, and subtle variants, the semantic set, and a focus ring.

Author in a perceptually uniform color space where the toolchain supports
it, so that a lightness step means the same visual change at every hue.
Derive hover and active states by adjusting lightness within the space
rather than hand-picking unrelated values, and let the platform's color
mixing do the derivation so the relationship survives a token change.

## Both themes, from the start

Design light and dark together. Retrofitting a theme produces the
characteristic result where one mode is designed and the other is inverted.

* Never pure black or pure white for large surfaces. Pure black kills depth
  and causes smearing on some displays; pure white glares. Use a near-black
  and a near-white.
* Dark mode is not an inversion. Elevation reverses: raised surfaces get
  lighter, not darker, and shadows do less work, so borders and surface
  lightness carry elevation instead.
* Saturated colors vibrate against dark backgrounds. Reduce saturation and
  raise lightness for accents in dark mode rather than reusing the light
  value.
* Hierarchy parity is the requirement: whatever draws the eye first in light
  draws it first in dark.
* Prefer the platform's mechanism for selecting between theme values in one
  declaration, and respect the system preference by default. Add an explicit
  toggle when either mode loses meaningful brand expression, and persist the
  choice.

## Contrast thresholds

Canonical values. Compute the ratio; never estimate it, and never accept a
document's claim about it.

| Applies to | Minimum | Source |
| --- | --- | --- |
| Text below the large-text size | 4.5:1 | WCAG 2.2 SC 1.4.3, level AA |
| Large text: 24px, or 18.66px at bold | 3:1 | WCAG 2.2 SC 1.4.3, level AA |
| Visual information identifying a control or its state | 3:1 | WCAG 2.2 SC 1.4.11, level AA |
| Parts of a graphic required to understand content | 3:1 | WCAG 2.2 SC 1.4.11, level AA |

Exempt, per those criteria: disabled and otherwise inactive controls, pure
decoration, text inside a logotype, and graphics whose exact presentation is
essential. A divider drawn between two same-elevation surfaces is decoration
and is exempt; the border that tells a user where an input begins is not.

Consequences worth stating, because these are the commonly missed cases:

* An accent that fails at body size frequently passes at display size. Size
  is part of the measurement, so the same color can be compliant in a
  headline and non-compliant in a button label.
* Placeholder, helper, and secondary text are styled to look secondary and
  then never measured. Measure them against every surface they appear on,
  including tinted cards, not only against the page background.
* Measure the composited result wherever transparency is involved.
* Text over imagery needs a guaranteed backing: a scrim, a gradient, or a
  solid panel. Contrast against an image's average color is not contrast
  against the pixels behind the letters.
* Color is never the only channel. Pair it with text, icon, weight, or
  position.
* Keep forced-colors and high-contrast modes functional rather than
  overriding the system keywords.

## Choosing a palette

Let the brand, domain, and audience choose. When nothing constrains the
choice, avoid the reflexive families of generated design: the purple-to-blue
technology gradient, and the warm cream with brass and oxblood that appears
on every artisan and premium consumer brief. Both are recognizable defaults
rather than decisions, and they make distinct brands look identical.

Choose instead by asking what the brand is not, then find a direction that
is coherent and unusual for the category: a saturated single hue against one
neutral, a deep natural tone with a warm accent, sharp near-black against a
warm mid-tone, or true monochrome with one bright accent. Rotate across
projects; shipping the same palette twice in a category means the palette
came from habit.

## Failure modes

* An accent chosen for the button, then a different one for links, then a
  third for charts.
* Grey text lightened until it looks refined and fails contrast.
* Semantic colors indistinguishable from the accent, so nothing reads as an
  alert.
* A dark theme built by inverting lightness, leaving shadows invisible and
  accents vibrating.
* Gradients used to add interest to a composition that lacks hierarchy.
