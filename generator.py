import generator.parser


if __name__ == '__main__':
    print('------------------------')
    print('CLIENT-BOUND DEFINITIONS')
    print('------------------------')
    with open('generator/clientbound.mbm') as f:
        for definition in generator.parser.parse_str(f.read()):
            print(definition)
            print()

    print('------------------------')
    print('SERVER-BOUND DEFINITIONS')
    print('------------------------')
    with open('generator/serverbound.mbm') as f:
        for definition in generator.parser.parse_str(f.read()):
            print(definition)
            print()
