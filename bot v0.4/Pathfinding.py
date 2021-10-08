#Path finding File
def get_closest_resource(unit, resource_tiles, player):
    global status
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
    if status.clusterflag:
        get_rescoure_cluster(closest_resource_tile, [])            
    return closest_resource_tile

def get_closest_city_tile(player,unit):
    closest_dist = math.inf
    closest_city_tile = None
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            dist = city_tile.pos.distance_to(unit.pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_city_tile = city_tile
    return closest_city_tile

def get_closest_empty_city_tile(player,unit):
    closest_dist = math.inf
    closest_city_tile = None

    unit_pos_list = []
    for u in player.units:
        unit_pos_list.append(u.pos)
    log_function(f"Unit pos list {unit_pos_list}")
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            dist = city_tile.pos.distance_to(unit.pos)
            if (dist < closest_dist) and (city_tile.pos not in unit_pos_list):
                closest_dist = dist
                closest_city_tile = city_tile
    return closest_city_tile

def get_simple_path(unit, dest):
    global game_state
    (dx, dy) = (dest.pos.x-unit.pos.x, dest.pos.y-unit.pos.y)
    sign = lambda a: (a>0) - (a<0)
    log_function(f"unit pos = {unit.pos.x, unit.pos.y}, dx = {dx}, dy = {dy}")
    cell_x_dir = game_state.map.get_cell(unit.pos.x+sign(dx), unit.pos.y)
    cell_y_dir = game_state.map.get_cell(unit.pos.x, unit.pos.y+sign(dy))
    if (not dx) or cell_x_dir.citytile:
        log_function(f"moving to {[cell_y_dir.pos.x,cell_y_dir.pos.y]}")
        return cell_y_dir
    elif dx:
        log_function(f"moving to {[cell_x_dir.pos.x,cell_x_dir.pos.y-sign(dy)]}")
        return cell_x_dir

def get_better_path(unit, dest):
    global game_state
    (dx, dy) = (dest.pos.x-unit.pos.x, dest.pos.y-unit.pos.y)
    better_path = None
    path_list = [[game_state.map.get_cell_by_pos(unit.pos)]]
    visited = []
    log_function(f"---- get_better_path ----\nunit pos = {(unit.pos.x,unit.pos.y)} to {dest.pos.x,dest.pos.y}")
    while not better_path:
        full_new_path_list = []
        for p in path_list:
            new_path_list = []
            curr_path_cor = []
            for n in p:
                curr_path_cor.append((n.pos.x, n.pos.y))
            current_cell = p[-1]
            #log_function(f" current cell = {current_cell.pos.x,current_cell.pos.y}")
            adj_cells = get_build_grid(current_cell,1)
            for i in adj_cells:
                try:
                    check_cell = i
                    if check_cell.pos.equals(dest.pos):
                        better_path = p + [check_cell]
                        #log_function(f"***** best path found ***** {better_path=}")
                        break
                    elif check_cell.citytile or check_cell in visited:
                        continue
                    else:
                        check_path = p
                        check_path= p + [check_cell]
                        new_path_list.append(check_path)
                        visited.append(check_cell)
                except Exception as e:
                    log_function(f"Better path ref out of index {str(e)}")
            for j in new_path_list:
                full_new_path_list.append(j)
            
        path_list = full_new_path_list
        
    log_function(f"Best path from {(unit.pos.x,unit.pos.y)} to {dest.pos.x,dest.pos.y} is:")
    for i in better_path:
        log_function(f" ({i.pos.x,i.pos.y})")
    if len(better_path) >= 2:
        log_function(f"next pos ({better_path[1].pos.x,better_path[1].pos.y})")
        return better_path[1]
    else:
        log_function(f"next pos ({better_path[0].pos.x,better_path[0].pos.y})")
        return better_path[0]