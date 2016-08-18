def pluralize(something):
    if not isinstance(something, list):
        something = [something]
    return something
