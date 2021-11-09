
def move_manager(player, move_list):
    return move_list
    unit_dict = {}
    new_pos_list = []
    adjusted_move_list = []
    for unit in player.units:
        unit_dict[unit.id] = unit.pos
    return move_list
    for move in move_list:
        act = move.split()[0]
        if act == "m":
            u_id = move.split()[1]
            dir = move.split()[2]
            new_pos = unit_dict[u_id].translate(dir,1)
            if new_pos not in new_pos_list:
                pass
            else:
                adjusted_move_list.append(move)
        else: adjusted_move_list.append(move)
    log_function(f"{adjusted_move_list=}")
    return adjusted_move_list