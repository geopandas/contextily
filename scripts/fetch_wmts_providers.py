from copy import deepcopy
import json
import itertools
import projecttile as pt

import parse_leaflet_providers


def starts_with_digit(name):
    try:
        int(name[0])
        return True
    except ValueError:
        return False


def process_metadata(
    basename,
    provider_metadata,
    tilematrixsets,
    prepend=None,
    base_url=None,
    attribution=None,
):
    """
    Arguments
    ---------
    basename : str
        basename of the Bunch
    provider_metadat : dict
        contains the metadata of all content the WMTS service provides
    tilematrixsets : dict
        contains the metadata of the matrixsets the WMTS service provides
    prepend : string, optional
        the WTMS layers may start with digits, which results in invalid Python
        variable names. This is prepended with this string in case the name
        starts with a digit.
    base_url : string, optional
        Depending on the service, URLs are provided as ResourceURLs, or they 
        should **hopefully** follows WMTS specs in which case they have a single
        root base_url.
    attribution : string, optional
        attribution to include. WMTS services do not appear to give proper 
        attribution info, so it has to be added manually.

    Returns
    -------
    providers : dict of dicts
        Contains the provider metadata, ready to dump as json into the _providers.py module.
    """

    # Avoid side-effects
    provider_metadata = deepcopy(provider_metadata)
    providers = {}

    for name, d in data.items():
        # Get rid of 8 bit pngs
        if len(d["formats"]) > 1:
            try:
                d["formats"].pop("image/png8")
            except:
                pass
        # Don't combine bounding box:
        bbox = d.pop("bboxWGS84")
        combinations = [dict(zip(d, v)) for v in itertools.product(*d.values())]

        for item in combinations:
            setname = item["tilematrixset"]
            # Colons might be problematic in the names?
            provider_name = name + "_" + setname.replace(":", "_")

            if starts_with_digit(provider_name):
                provider_name = prepend + provider_name

            tilematrixset = tilematrixsets[setname]
            provider_crs = tilematrixset["crs"]
            # Remove weird double colon
            provider_crs = "EPSG:" + provider_crs.split("EPSG::")[-1]
            left, bottom, right, top = pt.provider_bounds(bbox, provider_crs)
            bounds = [[left, bottom], [right, top]]

            url = item.get("url")
            if url is None:
                url = base_url

            provider = dict(
                url=url,
                min_zoom=tilematrixset["min_zoom"],
                max_zoom=tilematrixset["max_zoom"],
                bounds=bounds,
                variant=name,
                style=item["styles"],
                tilematrixset=setname,
                crs=provider_crs,
                format=item["formats"],
                name=basename + "." + provider_name,
            )
            if attribution is not None:
                provider["attribution"] = attribution

            providers[provider_name] = provider

    return providers


if __name__ == "__main__":
    # Get capabilities
    url = "https://geodata.nationaalgeoregister.nl/tiles/service/wmts?"
    # Fetch data
    data, tilematrixsets = pt.wmts_metadata(url)

    base_url = (
        "https://geodata.nationaalgeoregister.nl/tiles/service/wmts?"
        "SERVICE=WMTS"
        "&REQUEST=GetTile"
        "&VERSION=1.0.0"
        "&LAYER={variant}"
        "&STYLE={style}"
        "&TILEMATRIXSET={tilematrixset}"
        "&TILEMATRIX={tilematrixset}:{z}"
        "&TILEROW={y}"
        "&TILECOL={x}"
        "&FORMAT={format}"
    )
    attribution = "Kaartgegevens (C) Kadaster"
    nlmaps_providers = process_metadata(
        basename="PDOK",
        provider_metadata=data,
        tilematrixsets=tilematrixsets,
        prepend="nl",
        base_url=base_url,
        attribution=attribution,
    )

    # Write to file
    content = parse_leaflet_providers.generate_file(
        {"PDOK": nlmaps_providers}, description=url
    )
    with open("_nl_providers.py", "w") as f:
        f.write(content)
