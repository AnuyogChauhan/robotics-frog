





def main():
    template = open('robot_ens_server.py', 'r')
    templateText = ""
    for l in template.readlines():
        templateText += l
    template.close()

    mathcode = open('robotcalc.py', 'r')
    mathText = ""
    for m in mathcode.readlines():
        mathText += m

    mathcode.close()
    mathText = '\n\n' + mathText
    templateText = templateText.replace("##ANGLEDISTANCE_PLACEHOLDER###", mathText)
    output = open('output.py', 'w')
    output.write(templateText)
    output.close()


if __name__ == "__main__":
    main()

