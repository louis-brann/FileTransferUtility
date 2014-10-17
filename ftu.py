# Ben Goldberg and Louie Brann
# File Transfer Utility

import socket
import pickle
import copy
import sys
import os

def main(argv):
    udpPort  = 44000
    tcpPort  = 44001
    louieIP  = "134.173.42.215"
    benIP    = "134.173.42.9"
    filePath = "/mnt/home/bgoldberg/Desktop/CS125/FileTransferUtility/example.txt"
    fileName = "example.txt"
    allDone  = False
    
    #Receiver
    if len(argv) == 1:

        #make UDP socket
        udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpSocket.bind(("", udpPort))

        #make TCP socket
        tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSocket.bind(("", tcpPort))
        tcpSocket.listen(1)

        #TCP: Accept incoming handshake 
        establishedTcp, addr = tcpSocket.accept()

        fileMetadataPickled = establishedTcp.recv(1024)
        if not fileMetadataPickled:
            print "no data"
        fileMetadata = pickle.loads(fileMetadataPickled)
        print fileMetadata

        #Make datastructures to put data from udpSocket
        fileBuffer = [fileMetadata[1]]
        while True:

            currentPacketPickled, addr = udpSocket.recvfrom(1024)
            packetIndex, packetData = pickle.loads(currentPacketPickled)

            fileBuffer[packetIndex] = copy.deepCopy(packetData)
           
            break
        print fileBuffer


    #Sender
    else:
        # #parse command line inputs
        # if len(argv) == 3:
        #     source = argv[1]
        #     dest = argv[2]
        # else:
        #     print 'ftu.py <source> <dest>'
        #     sys.exit(2)
        
        
        #make UDP socket
        udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        #make TCP socket
        tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSocket.connect((benIP, tcpPort))

        #get filesize
        fileSize = os.path.getsize(filePath)
        fileMetadata = (fileName, fileSize)

        #TCP: Send fileName and fileSize
        fileMetadataPickled = pickle.dumps(fileMetadata)
        tcpSocket.send(fileMetadataPickled)

        #Open file and put data into dataToSend
        inFile = open(fileName, r)
        dataToSend = inFile.read()

        #UDP: send pickled data
        dataToSendPickled = pickle.dumps(dataToSend)
        udpSocket.sendto(dataToSendPickled, (benIP,udpPort))






if __name__ == "__main__":
    main() 