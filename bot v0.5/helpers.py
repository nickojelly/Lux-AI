def get_closest_resource(unit, resource_tiles, player):
    global clusterflag
    closest_dist = math.inf
    closest_resource_tile = None

    unit_pos_list = []
    for u in player.units:
        unit_pos_list.append(u.pos)
    if unit.get_cargo_space_left() > 0:
        # if the unit is a worker and we have space in cargo, lets find the nearest resource tile and try to mine it
        for resource_tile in resource_tiles:
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
            dist = resource_tile.pos.distance_to(unit.pos)
            if dist < closest_dist and resource_tile.pos not in unit_pos_list:
                closest_dist = dist
                closest_resource_tile = resource_tile
    if clusterflag:
        get_rescoure_cluster(closest_resource_tile, [])            
    return closest_resource_tile