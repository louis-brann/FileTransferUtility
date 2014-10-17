# Ben Goldberg and Louie Brann
# File Transfer Utility

import socket
import pickle
import copy
import sys
import numpy
import os

def main(argv):
    udpPort  = 44000
    tcpPort  = 44001
    louieIP  = "134.173.42.215"
    benIP    = "134.173.42.9"
    filePath = "/Users/Guest/Desktop/FileTransferUtility/example.txt"
    fileName = "example.txt"
    allDone  = False
    
    #Receiver
    if len(argv) == 0:

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
        fileName, fileSize = fileMetadata
        numPackets = math.ceil(float(fileSize) / float(packetSize))
        fileBuffer = [numPackets]
        while True:
            # Receive packet
            currentPacketPickled, addr = udpSocket.recvfrom(1024)
            currentPacket = pickle.loads(currentPacketPickled)

            # Put packet data into file buffer
            packetIndex, packetData = currentPacket
            fileBuffer[packetIndex] = copy.deepcopy(packetData)
           
            break

        print fileBuffer

        outFile = open(fileName, 'wb')
        ndarray.tofile(outFile)


    #Sender
    else:
        # #parse command line inputs
        # if len(argv) == 2:
        #     source = argv[0]
        #     dest = argv[1]
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
        inFile = open(fileName, 'r')
        dataToSend = inFile.read()

        dataToSend = (0, dataToSend)

        #UDP: send pickled data
        dataToSendPickled = pickle.dumps(dataToSend)
        udpSocket.sendto(dataToSendPickled, (benIP,udpPort))






if __name__ == "__main__":
    main(sys.argv[1:]) 