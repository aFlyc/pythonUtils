import re

# 寻找两个正则表达式的内容（非贪婪匹配）
def findContentBetweenTwoPattern(lines, leftPattern, rightPattern):
    content = ''
    matchedLeftPattern = False
    for line in lines:
        leftPatternSearchResult = re.search(leftPattern, line)
        if leftPatternSearchResult:
            content += line[leftPatternSearchResult.end():]
            matchedLeftPattern = True
        
        if matchedLeftPattern:
            rightPatternSearchResult = re.search(rightPattern, line)
            if rightPatternSearchResult:
                if not leftPatternSearchResult:
                    content += line[0:rightPatternSearchResult.start()]
                else:
                    content = content[0: re.search(rightPattern, content).start()]
                break

            if not leftPatternSearchResult:
                content += line
    return content