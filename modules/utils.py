SEASON_UPDATE = {"monitored": False}


def manage_seasons(seasons):
    sorted_seasons = sorted(seasons, key=lambda s: s.get("seasonNumber"))
    edited_seasons = [{**season, **SEASON_UPDATE} for season in sorted_seasons]
    edited_seasons[-1]['monitored'] = True
    return edited_seasons
