# Data Notice — Cancer Incidence in Five Continents (CI5)

HerediCalc's incidence-source plugins are driven by data from **Cancer Incidence in
Five Continents (CI5)**, published by the **International Agency for Research on
Cancer (IARC / WHO)**. This data is **© IARC** and is governed by IARC's terms of
use, which are independent of this repository's MIT code license.

**The CI5 data is NOT distributed with this repository.** Obtain it separately,
directly from IARC, under the terms below.

## IARC terms of use

> Before downloading the files, please note that they may be freely used but not for
> sale or for use in conjunction with commercial or promotional purposes, and provided
> any use shall be subject to appropriate reference and acknowledgement of the source.

Source pages: <https://ci5.iarc.who.int/> (data host: `https://gco.iarc.fr/media/ci5/`).
Questions about reuse may be directed to IARC at `ci5@iarc.fr`.

## How to obtain the data

Run the fetch script from the repository root:

```bash
python scripts/fetch_ci5_data.py
```

This downloads IARC's five "detailed database" ZIPs, unpacks them, and copies the
payload **byte-for-byte** into the plugin `data/` directories — no transformation is
performed. Each fetched file is then verified (SHA-256) against
`scripts/ci5_checksums.txt`; the run succeeds only if all 1785 expected files match
exactly. Use `--target DIR` to write the tree somewhere other than the repository.

By running the script you obtain the data directly from IARC and are bound by IARC's
terms of use quoted above.

## Recommended citation (per volume)

The following are IARC's recommended citations for the electronic data, as listed at
<https://ci5.iarc.fr/ci5plus/references/>. Cite the volume(s) you use.

- **Vol. VIII** — Parkin, D.M., Whelan, S.L., Ferlay, J., Teppo, L., and Thomas, D.B.,
  eds (2002), *Cancer Incidence in Five Continents, Vol. VIII*, IARC Scientific
  Publications, No. 155, Lyon, IARC.
- **Vol. IX** — Curado, M.P., Edwards, B., Shin, H.R., Storm, H., Ferlay, J., Heanue,
  M., and Boyle, P., eds (2007), *Cancer Incidence in Five Continents, Vol. IX*, IARC
  Scientific Publications, No. 160, Lyon, IARC.
- **Vol. X** — Forman, D., Bray, F., Brewster, D.H., Gombe Mbalawa, C., Kohler, B.,
  Piñeros, M., Steliarova-Foucher, E., Swaminathan, R., and Ferlay, J., editors (2014),
  *Cancer Incidence in Five Continents, Vol. X*, IARC Scientific Publication No. 164.
  Lyon: International Agency for Research on Cancer.
- **Vol. XI** — Bray, F., Colombet, M., Mery, L., Piñeros, M., Znaor, A., Zanetti, R.,
  and Ferlay, J., editors (2017), *Cancer Incidence in Five Continents, Vol. XI*
  (electronic version). Lyon: International Agency for Research on Cancer.
  (Print edition: IARC Scientific Publication No. 166.)
- **Vol. XII** — Bray, F., Colombet, M., Aitken, J.F., Bardot, A., Eser, S., Galceran,
  J., Hagenimana, M., Matsuda, T., Mery, L., Piñeros, M., Soerjomataram, I., de Vries,
  E., Wiggins, C., Won, Y-J., Znaor, A., and Ferlay, J., editors (2023), *Cancer
  Incidence in Five Continents, Vol. XII* (IARC CancerBase No. 19). Lyon: International
  Agency for Research on Cancer. (Print edition: IARC Scientific Publication No. 169.)

## Note

This notice is informational and not legal advice. Before any redistribution or
commercial use of the CI5 data, confirm the terms with IARC.
