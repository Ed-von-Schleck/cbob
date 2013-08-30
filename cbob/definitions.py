SOURCE_FILE_EXTENSIONS = frozenset((".c", ".cpp", ".cxx", ".c++", ".cc"))
HOOKS = frozenset(("pre_build", "post_build", "pre_add", "post_add"))
SYNONYMS = {
    "on": frozenset(("on", "true", "1", 1, "enabled", "yes")),
    "off": frozenset(("off", "false", "0", 0, "disabled", "no"))
}

