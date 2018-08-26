#!/usr/bin/python
# HTTP Header
#print ("Content-Type:application/octet-stream; name = \"FileName\"\r\n")
#print ("Content-Disposition: attachment; filename = \"FileName\"\r\n\n")
# Actual File Content will go here.
fo = open("foo.txt", "rb")
str = fo.read()
print (str)
# Close opend file
fo.close()