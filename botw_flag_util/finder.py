def find(args):
    search_name = args.flag_name
    bg_todelete: dict = util.search_bgdict(search_name)
    sv_todelete: dict = util.search_svdict(search_name)
    numbgkeys: int = 0
    numsvkeys: int = 0
    for _, flagdata in bg_todelete.items():
        numbgkeys += len(flagdata)
    for _, flagdata in sv_todelete.items():
        numsvkeys += len(flagdata)

    while True:
        print(
            f"\n{numbgkeys} gamedata flags and {numsvkeys} savedata flags were found that matched {search_name}."
        )
        print("\nPlease choose an option:")
        print("v - View the full flag names, files, and indices in their files")
        print("d - Delete these flags and exit")
        print("x - Exit without deleting the flags")
        selection = input("(v/d/x):")

        if selection == "v":
            for prefix, flagdata in bg_todelete.items():
                for hash in flagdata:
                    print(f"{bgdict[prefix][hash]['DataName']} in {prefix}")
            for file_name, flagdata in sv_todelete.items():
                for hash in flagdata:
                    print(f"{svdict[file_name][hash]['DataName']} in {file_name}")

        elif selection == "d":
            for prefix, flagdata in bg_todelete.items():
                for hash in flagdata:
                    util.rem_flag_bgdict(hash, prefix)
            for file_name, flagdata in sv_todelete.items():
                for hash in flagdata:
                    util.rem_flag_svdict(hash, file_name)
            return

        elif selection == "x":
            return
