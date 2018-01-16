import pytest, io, os


def walktree(top, callback, data, root=None):
    """Recursively descend the directory tree rooted at top,
       calling the callback function for each regular file."""
    if root is None:
        root = top
    for f in os.listdir(top):
        path = os.path.join(top, f)
        if os.path.isdir(path):
            # It's a directory, recurse into it
            walktree(path, callback, data, root)
        elif os.path.isfile(path):
            callback(path, data, root)
    return data


def strip_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def strip_suffix(text, suffix):
    if text.endswith(suffix):
        return text[:-len(suffix)]
    return text


def add_graphql_files_to_dict(pathname, file_dict, root):
    components_string = strip_prefix(pathname, root).lstrip('/')
    components = components_string.split('/')
    node = file_dict
    for component in components[:-1]:
        if component not in node.keys():
            node[component] = {}
        node = node[component]
    last_component = components[-1]
    with io.open(pathname, encoding='utf-8') as file_object:
        extension = '.graphql'
        if last_component.endswith(extension):
            key = strip_suffix(last_component, extension)
            node[key] = file_object.read()


registry_path = os.path.dirname(__file__) + '/../../static2/js/app/graphql'


@pytest.fixture(scope="session")
def graphql_registry():
    return walktree(registry_path, add_graphql_files_to_dict, {})
