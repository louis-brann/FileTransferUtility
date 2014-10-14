/**
 * \file ftu.cpp
 * \author Ben Goldberg and Louie Brann

 * \brief Reliable IP based File Transfer Utility. Maximized for use on
 *        100Mbit link with various levels of delay and packet loss.
 */

#include <stdio.h>
#include <iostream>
#include <unistd.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <netinet/in.h>
#include <fstream>
#include <pthread.h>
#include <vector>
#include <sstream>
#include <math.h>
using namespace std;

const int CONNECTIONS_ALLOWED = 1;
const char *TCP_PORT = "44000";
const char *UDP_PORT = "44001";
const int WINDOW_SIZE = 30;
const bool postMsg = 1;
const int packetSize = 1500;
bool allPacketsSignal = 0;

typedef struct {
    int fd;
    int totalPackets;
} tcpReceiverParams_t;

// TODO
typedef struct {
    int packetIndex;
    char *packet;
} dgram_t;


void usage() 
{
    cerr << "usage: ./ftu [-P port] [-v] \n"
         << "             [[user@]host1:]file1 ...[[user@]host2:]file2" << endl;
}


vector<int> parseMissedPackets(string &missedPacketsMsg)
{
    string missedPacketsCopy(missedPacketsMsg);
    vector<int> missedPackets;

    cout << "parsing missed packets!" << endl;
    while(true){
        int nextSpacePos = missedPacketsCopy.find(" ");

        if (nextSpacePos == -1){
            break;
        } else {
            missedPacketsCopy = missedPacketsCopy.substr(nextSpacePos+1);
        }

        int nextPacket = stoi(missedPacketsCopy.substr(0, nextSpacePos));

        missedPackets.push_back(nextPacket);

        
    }

    return missedPackets;
}


void sendPackets(ifstream &infile, int &udpFd, struct addrinfo *udpInfo, vector<int> &packetsToSend, int &totalPackets, int &length)
{
    int numPacketsToSend = packetsToSend.size();
    // For one window, send each packet
    for (int i = 0; i < numPacketsToSend; ++i)
    {
        cout << "starting forloop" << endl;
        // Set the infile to the correct place
        char packet[packetSize];
        infile.seekg(packetsToSend[i] * packetSize);
        int sendSize = packetSize;

        // Get packet index
        stringstream piStrStream;
        int packetIndex = i;
        piStrStream << packetIndex;
        string piStr = piStrStream.str();

        // Update sendSize if last packet
        if (packetsToSend[i] + 1 == totalPackets)
        {
            sendSize = length % packetSize;
        }
        
        int msgLength = sendSize + piStr.length() + 1;

        // Read in data from file
        infile.read(packet, sendSize);

        cout << "sendSize: " << sendSize << endl;
        const char* piCharStar = piStr.c_str();
        char *pi = const_cast<char *>(piCharStar);

        cout << "i is " << i << endl;
        cout << "pi is " << pi << endl;

        // Make msg in correct format (do the c-dance!)
        char *msg;
        if ((msg = (char *)malloc(msgLength)) != NULL)
        {
            msg[0] = '\0';
            strcat(msg, pi);
            strcat(msg, " ");
            strcat(msg, packet);
        }
   
        // msg[0] = '\0'
        // strcat(msg, " ");
        // strcat(msg, packet);

        cout << "sendSize: " << sendSize << endl;
        cout << "msg: " << msg << endl;

        // Send msg
        int sent = sendto(udpFd, msg, msgLength, 0, udpInfo->ai_addr, udpInfo->ai_addrlen);
        cout << "bytes sent: " << sent << endl;
    }
}


void *tcpReceive(void *arg)
{
    tcpReceiverParams_t *tcpReceiverParams = (tcpReceiverParams_t *)arg;
    int received = recv(tcpReceiverParams->fd, &tcpReceiverParams->totalPackets, sizeof tcpReceiverParams->totalPackets, 0);
    // cout << "TCP thread received bytes: " << received << endl;
    // cout << "TCP thread pre-change APS: " << allPacketsSignal << endl;
    allPacketsSignal = 1;
    // cout << "TCP thread post-change APS: " << allPacketsSignal << endl;
    return nullptr;
}


// Receives totalPackets packets from udp socket, then 
int receivePacket(int udpFd, struct addrinfo *udpInfo, char *receivedPackets[])
{
    cout << "receiving packet" << endl;
    
    // reserve space to represent any index in window, plus a separating space
    // int windowDigits = log10(WINDOW_SIZE) + 1;
    char msg[packetSize + 5];
    //char msg[packetSize + windowDigits + 1];
    
    // Receive the message
    int received = recvfrom(udpFd, msg, sizeof(msg), 0, udpInfo->ai_addr, &udpInfo->ai_addrlen);
    msg[received] = 0;

    cout << "msg: " << msg << endl;
    cout << "received " << received << " bytes" << endl;

    // Separate packet index from rest of string
    string msgStr(msg);
    int spacePos = msgStr.find(" ");
    string piStr = msgStr.substr(0, spacePos);
    int packetIndex = stoi(piStr);

    // Convert string to cstr to copy into array of packetes
    string actualMsg = msgStr.substr(spacePos+1);
    char *receivedPacket = const_cast<char *>(actualMsg.c_str());

    strncpy( receivedPackets[packetIndex] , receivedPacket, actualMsg.length());
    
    cout << "received packet: " << receivedPackets[0] << endl;

    return received;
}



// Loop through buffer checking what packets are missing
string getMissedPackets(int totalPackets, char *receivedPackets[])
{
    cout << "getting missed packets" << endl;
    string missingPackets = "";
    for (int i = 0; i < totalPackets; ++i)
    {
        if (receivedPackets+i == nullptr)
        {
            missingPackets += to_string(i);
            missingPackets += " ";
        }
    }
    
    return missingPackets;
}


int main(int argc, const char* argv[])
{
    bool debug = false;
    int portNumber;
    string source;
    string dest;
    vector<string> args(argv+1, argv+argc);

    // Process command line arguments
    for (int i = 1; i < argc; ++i) {
        string currentArg = args[i];
        if (currentArg.compare("-v") == 0) { //verbose
            debug = true;
        } else if (currentArg.compare("-P") == 0) { //port number
            portNumber = atoi(argv[++i]);
        } else {
            if (source.compare("") == 0){
                source = argv[i];
            } else if (dest.compare("") == 0){
                dest = argv[i];
            } else {
                cerr << argv[i] << " is not a valid option" << endl;
                usage();
            }
        }
    }

    // Parse dest into parts
    int colonPos = dest.find(":");
    string servName; 
    string destFile = dest;
    if (colonPos != -1)
    {
        servName = dest.substr(0, colonPos);
        destFile = dest.substr(colonPos+1);

        cout << "destFile before file check: " << destFile << endl;

        if (destFile.find(".") == -1)
        {
            int srcColonPos = source.find(":");
            string origFileName = "";

            if (srcColonPos == -1)
            {
                origFileName = source;
            }
            else 
            {
                origFileName = source.substr(srcColonPos+1);
            }
            destFile += origFileName;
        }
        // TODO
        cout << "Server: " << servName << endl;
    }

    // Set up the dest file to have the same name as the original file
    
    cout << "Filename: " << destFile << endl;
    
    

    // Start setting up network stuff,
    int status;
    struct addrinfo tcpHint;
    struct addrinfo *tcpInfo;
    struct addrinfo udpHint;
    struct addrinfo *udpInfo;

    memset(&tcpHint, 0, sizeof tcpHint); // make sure the struct is empty
    tcpHint.ai_family = AF_UNSPEC;     // don't care IPv4 or IPv6
    tcpHint.ai_socktype = SOCK_STREAM; // TCP stream sockets
    tcpHint.ai_flags = AI_PASSIVE;     // fill in my IP for me

    memset(&udpHint, 0, sizeof udpHint); // make sure the struct is empty
    udpHint.ai_family = AF_UNSPEC;       // don't care IPv4 or IPv6
    udpHint.ai_socktype = SOCK_DGRAM;    // UDP stream sockets
    udpHint.ai_flags = AI_PASSIVE;       // fill in my IP for me

    // Server doesn't specify a source or a destination
    bool isServer = (source == "" && dest == "");
    if (isServer)
    {
        // TCP: Set up socket info
        if ((status = getaddrinfo(NULL, TCP_PORT, &tcpHint, &tcpInfo)) != 0) {
            cerr << "TCP: getaddrinfo error: " << gai_strerror(status) << endl;
            exit(status);
        }

        // UDP: Set up socket info 
        if ((status = getaddrinfo(NULL, UDP_PORT, &udpHint, &udpInfo)) != 0) {
            cerr << "UDP: getaddrinfo error: " << gai_strerror(status) << endl;
            exit(status);
        }

        int tcpFd, udpFd;
        int yes = 1;
        // TCP: loop through all the results and bind to the first we can
        struct addrinfo *p;
        for(p = tcpInfo; p != NULL; p = p->ai_next) {
            if ((tcpFd = socket(p->ai_family, p->ai_socktype,
                    p->ai_protocol)) == -1) {
                perror("TCP server: socket error");
                continue;
            }

            if (setsockopt(tcpFd, SOL_SOCKET, SO_REUSEADDR, &yes,
                    sizeof(int)) == -1) {
                perror("setsockopt");
                exit(1);
            }

            if (::bind(tcpFd, p->ai_addr, p->ai_addrlen) == -1) {
                close(tcpFd);
                perror("TCP server: bind error");
                continue;
            }

            break;
        }

        if (p == NULL)  {
            fprintf(stderr, "server: failed to bind\n");
            return 2;
        }

        // UDP: loop through all the results and bind to the first we can
        for(p = udpInfo; p != NULL; p = p->ai_next) {
            if ((udpFd = socket(p->ai_family, p->ai_socktype,
                    p->ai_protocol)) == -1) {
                perror("UDP server: socket error");
                continue;
            }

            if (::bind(udpFd, p->ai_addr, p->ai_addrlen) == -1) 
            {
                close(udpFd);
                perror("UDP server: bind error");
                continue;
            }

            break;
        }

        while(true)
        {
            // TCP: Start listening
            if ((status = listen(tcpFd, CONNECTIONS_ALLOWED)) == -1) 
            {
                cerr << "TCP: Failed listening with error: " << status << endl;
                exit(status);
            }

            cout << "Setup complete. Listening" << endl;

            // TCP: accept connection
            socklen_t tcpAddrSize = sizeof tcpInfo;
            int establishedTcpFd = accept(tcpFd, (sockaddr *)tcpInfo, &tcpAddrSize);
            if (establishedTcpFd == -1)
            {
                cerr << "TCP: Accept failed, trying again";
                continue;
            }

            cout << "Accepted eTcpFd: " << establishedTcpFd << endl;


            // TCP: receive number of packets to be sent
            uint32_t totalPacketsBuf;
            int received = recv(establishedTcpFd, &totalPacketsBuf, sizeof (uint32_t), 0);
            cout << "bytes received: " << received << endl;
            int totalPackets = (int)ntohl(totalPacketsBuf);

            cout << "Got num packets: " << totalPackets << endl;

            // TCP: Receive file name
            int error = recv(establishedTcpFd, &destFile, sizeof(destFile), 0);
            if (error == -1)
            {
                cout << "Error receiving file name" << endl;
                exit(1);
            }
            cout << "TCP: Received filename: " << destFile << endl;

            
            int goAhead = 1;
            int sent = send(establishedTcpFd, &goAhead, sizeof goAhead, 0);
            cout << "Sent go-ahead to: " << establishedTcpFd << endl;

            // UDP: Receive ALL packets
            // TODO: update for buffer not entire file
            int windowOffset = 0;
            int bytesRead = 0;
            char *receivedPackets[totalPackets];
            // for (int i = 0; i < totalPackets; ++i)
            // {
            //     receivedPackets[totalPackets] = (char *)malloc(packetSize);
            // }

            ofstream outFile;
            cout << "destfile: " << destFile << endl;
            outFile.open(destFile, ios::out|ios::binary);

            // Listen for one set of packets
            
            while(true)
            {
                // Make new thread to listen for TCP connection
                tcpReceiverParams_t tcpReceiverParams;
                tcpReceiverParams.fd = establishedTcpFd;
                tcpReceiverParams.totalPackets = totalPackets;

                pthread_t tcpReceiver;
                if (int err_code = pthread_create(&tcpReceiver, NULL, tcpReceive, &tcpReceiverParams))
                {
                    cerr << "Error making new thread \n";
                    exit(err_code);
                }

                string missingPackets;
                
                while(true)
                {
                    cout << "allPacketsSignal main thread: " << allPacketsSignal << endl;
                    // If they aren't done sending, receive more packets
                    if (allPacketsSignal == 0) 
                    {   
                        // fd_set read_flags,write_flags; // the flag sets to be used
                        // struct timeval waitd;          // the max wait time for an event
                        // int sel;                      // holds return value for select();

                        // waitd.tv_sec = 5;
                        // FD_ZERO(&read_flags);
                        // FD_SET(udpFd, &read_flags);
                        // if ((sel = select(udpFd+1, &read_flags, NULL, NULL, &waitd)) <= 0)
                        // {
                        //     cout << " updating aps: " << allPacketsSignal << endl;
                        //     cout << "sel is: " << sel << endl;
                        //     continue;
                        // }
                        // cout << "sel is: " << sel << endl;
                        bytesRead += receivePacket(udpFd, udpInfo, receivedPackets);
                    } 
                    // Otherwise, send what we're missing
                    else 
                    {
                        missingPackets = getMissedPackets(totalPackets, receivedPackets);
                        send(establishedTcpFd, &missingPackets, sizeof missingPackets, 0);
                        break;
                    }
                }

                cout << "out of receiving packets loop" << endl;
                 // If we've read all the packets in this window, reap thread
                if(int err_code = pthread_join(tcpReceiver, NULL))
                {
                    cerr << "Couldn't join! \n";
                    exit(err_code);
                }
                cout << "joined pthread" << endl;                
                allPacketsSignal = 0;

                // If the buffer is full, write it to the file
                if (missingPackets.length() == 0)
                {
                   
                    close(establishedTcpFd);

                    cout << "empty missing packets " << endl;
                    cout << "total packets: " << totalPackets << endl;
                    // Update to work for buffer (extra offset that gets incremented per file read)   
                    for (int i = 0; i < totalPackets; ++i)
                    {
                        outFile.seekp(windowOffset + i*packetSize);
                        cout << "outFile offset: " << outFile.tellp() << endl;
                        cout << "bytesRead: " << bytesRead << endl;
                        outFile.write(receivedPackets[i], bytesRead);
                    }
                    outFile.close();

                    break;
                }
            }
        }
    } 
    // If source and dest aren't empty, this is the sender
    else 
    { 
        char *serv;
        if (servName.length() == 0)
        {
            serv = NULL;
        } 
        else 
        {
            serv = const_cast<char *>(servName.c_str());
            cout << "Serv is: " << serv << endl;
        }


        // TCP: set up socket info
        if ((status = getaddrinfo(serv, TCP_PORT, &tcpHint, &tcpInfo)) != 0) {
            cerr << "TCP: getaddrinfo error: " << gai_strerror(status) << endl;
            exit(status);
        }

        // UDP: set up socket info
        if ((status = getaddrinfo(serv, UDP_PORT, &udpHint, &udpInfo)) != 0) {
            cerr << "UDP: getaddrinfo error: " << gai_strerror(status) << endl;
            exit(status);
        }

        // TCP: loop through all the results and connect to the first we can
        struct addrinfo *p;
        int tcpFd, udpFd;
        for(p = tcpInfo; p != NULL; p = p->ai_next) {
            if ((tcpFd = socket(p->ai_family, p->ai_socktype,
                    p->ai_protocol)) == -1) {
                perror("TCP client: socket error");
                continue;
            }

            if (connect(tcpFd, p->ai_addr, p->ai_addrlen) == -1) {
                close(tcpFd);
                perror("TCP client: connect error");
                continue;
            }

            break;
        }

        if (p == NULL) {
            fprintf(stderr, "TCP client: failed to connect\n");
            return 2;
        }

        // UDP: loop through all the results and bind to the first we can
        for(p = udpInfo; p != NULL; p = p->ai_next) {
            if ((udpFd = socket(p->ai_family, p->ai_socktype,
                    p->ai_protocol)) == -1) {
                perror("UDP client: socket error");
                continue;
            }

            break;
        }

        if (p == NULL) {
            fprintf(stderr, "UDP client: failed to bind socket\n");
            return 2;
        }

        // cout << "accepted tcp: " << establishedTcpFd << endl;
        // TODO
        // Send source, dest
        // send file name from source
        // send dest name 

        // Open the file
        ifstream myFile;
        myFile.open(source, ios::in|ios::binary|ios::ate);

        // Get size of the file
        myFile.seekg(0, myFile.end);
        int length = myFile.tellg();
        myFile.seekg(0, myFile.beg);
        int totalPackets = ceil((float)length / (float)packetSize);

        cout << "length: " << length << endl;

        cout << "totalPackets: " << totalPackets << endl;

        // Initially they're missing all packets
        vector<int> packetsToSend;
        for (int i = 0; i < totalPackets; ++i)
        {
            packetsToSend.push_back(i);
        }

        int goAhead;
        // Send all packets
        while (packetsToSend.size() > 0)
        {
            // TCP: Notify of how many packets are about to be sent
            uint32_t totalPacketsBuf = htonl(totalPackets);
            cout << "totalPacketsBuf: " << totalPacketsBuf << endl;
            int sent = send(tcpFd, &totalPacketsBuf, sizeof totalPackets, 0);
            cout << "bytes sent: " << sent << endl;

            // TCP: Send file name
            cout << "destFile: " << destFile << endl;
            send(tcpFd, &destFile, sizeof destFile, 0);

            // TCP: Receive go-ahead response
            int received = recv(tcpFd, &goAhead, sizeof goAhead, 0);
            cout << "Bytes received: " << received << endl;
            if (goAhead == 0)
            {
                cerr << "Connection denied!";
                exit(1);
            }

            // UDP: Send data
            sendPackets(myFile, udpFd, udpInfo, packetsToSend, totalPackets, length);

            cout << "1 set of udp packets sent!" << endl;
            usleep(1000000);

            // TCP: Done sending
            send(tcpFd, &postMsg, sizeof postMsg, 0);



            // TCP: Receive missed packets message
            string missedPackets;
            recv(tcpFd, &missedPackets, sizeof missedPackets, 0);
            packetsToSend = parseMissedPackets(missedPackets);
        }

        // Close all established connections
        close(tcpFd);
        close(udpFd);
        //close(tcpFd);
    }

    // Free the memory
    freeaddrinfo(tcpInfo); 
    freeaddrinfo(udpInfo); 

    return 0;
}


