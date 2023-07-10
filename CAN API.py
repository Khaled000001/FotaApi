import can
import os
from can import *
from threading import Thread
import json
import base64
import time

# ----------------Version State-----------------
VERSION_FULLUPDATE = 0x1
VERSION_NEWFEATURES = 0x2
VERSION_PATCH = 0x3
VERSION_NOCHANGE = 0x4
VERSION_ROLLBACK = 0x5

# -------------------CAR INFO-------------------
CAR_ID = 1
ECU_ID = 1
# -------------------CAN IDs--------------------
LOGIN_ID = 0x1
SIGNUP_ID = 0x2
CHECKUPDATE_ID = 0x3
DATA_ID = 0x6
UPDATE_ID = 0x4
ECU_DIAGNOSTIC_LOG_ID = 22
DIAGNOSTIC_RQ_ID = 5
# -----------------CAN FILTERS------------------

filters = [
    {"can_id": LOGIN_ID, "can_mask": 0xFFF, "extended": False},
    {"can_id": DATA_ID, "can_mask": 0xFFF, "extended": False},
    {"can_id": UPDATE_ID, "can_mask": 0xFFF, "extended": False},
    {"can_id": CHECKUPDATE_ID, "can_mask": 0xFFF, "extended": False},
    {"can_id": DIAGNOSTIC_RQ_ID, "can_mask": 0xFFF, "extended": False},

]


class CanApi:

    #
    # def main():
    #     os.system("sudo ip link set can0 down")
    #     os.system("sudo ip link set can0 up type can bitrate 125000")
    #     bus = can.ThreadSafeBus(channel='can0', bustype='socketcan', bitrate='125000', can_filters=filters)
    #
    #     status, date = UserLogin(bus, "user1", "password")
    #     print("Login Status = " + str(status) + "\nDate = " + date)
    #
    #     # status = UserSignup(bus, "mohamed65", "1234", "12342", 121)
    #     # print("SignUp Status = " + str(status))
    #     if status == 200:
    #         statusCode, firmwareInfo, updateState = CheckUpdate(bus, 1, 1)
    #         ##print("firmware_version = " + firmwareInfo['firmware_version'] + "\nfirmware_id = " + str(firmwareInfo['firmware_id']) + "\ndescription = " + base64.b64decode(firmwareInfo['description'].encode()).decode() + "\nUpdateState = " +str(updateState))
    #     state, mythread = DownloadUpdate(bus, "3")
    #     if state is not None:
    #         print(str(state))
    #         mythread.join()
    #         #    print("firmware_version = " + json_obj['firmware_version'] + "\nfirmware_id = " + str(json_obj['firmware_id']) + "\ndescription = " + base64.b64decode(json_obj['description'].encode()).decode())
    #     # print("In While one")
    #     # while True:
    #     #    pass
    #     # diagFile = GetECU_Diagnostic(bus, 22)
    #     # if diagFile is None:
    #     #    print("Error!")
    #     # print(diagFile + "\n")
    #     # Base64File = base64.b64encode(diagFile.encode()).decode()
    #     # status = SendDiagnostic(bus, 23, 22, Base64File)
    #     # print("\nDiagnostic Status = " + str(status))
    #
    #     bus.shutdown()

    def __init__(self):
        os.system("sudo ip link set can0 down")
        os.system("sudo ip link set can0 up type can bitrate 125000")
        self.bus = can.interface.Bus(channel='can0', bustype='socketcan', bitrate='125000', can_filters=filters)
        self.firmwareSize = 0

    def CheckUpdate(self, car_id: int, ecu_id: int):
        reader = can.BufferedReader()
        notifier = Notifier(self.bus, [reader])

        metaData = f'car_id={car_id}&ecu_id={ecu_id}'
        metaDataLength = len(metaData)
        msg = can.Message(arbitration_id=CHECKUPDATE_ID, is_extended_id=False, dlc=2,
                          data=[(0xFF & metaDataLength), (0xFF00 & metaDataLength) >> 8])
        self.bus.send(msg)
        self.sendStr(self.bus, metaData, DATA_ID)
        response_msg = reader.get_message(timeout=15)
        if response_msg == None:
            notifier.stop()
            print("failed to receive status code Timeout")
            return 0, "Invalid", None
        statusCode = response_msg.data[0] | (response_msg.data[1] << 8)
        if statusCode != 200:
            notifier.stop()
            print("check update status = " + str(statusCode))
            return statusCode, "Invalid", None

        updateState_msg = reader.get_message(timeout=15)
        updateState = updateState_msg.data[0]
        if updateState == VERSION_NOCHANGE:
            print("No update is founded")
            notifier.stop()
            return statusCode, "Invalid", updateState
        firmwareInfoSize_msg = reader.get_message(timeout=15)
        firmwareInfoSize = firmwareInfoSize_msg.data[0] | firmwareInfoSize_msg.data[1] << 8

        firmwareInfo = b''
        while True:
            message = reader.get_message(timeout=15)
            if message == None:
                print("Timeout while receiving firmwareInfo, received Data Size =" + str(len(firmwareInfo)) + "/" + str(
                    firmwareInfoSize))
                notifier.stop()
                return statusCode, "Invalid", updateState
            firmwareInfo += message.data
            if len(firmwareInfo) >= firmwareInfoSize:
                break
        json_obj = json.loads(firmwareInfo.decode())

        print("firmware update check Done!")
        notifier.stop()
        return statusCode, json_obj, updateState

    def sendStr(self, string: str, id: int):
        msg = can.Message(arbitration_id=id, is_extended_id=False, dlc=8, data=[0] * 8)
        for i in range(0, len(string), 8):
            chunk = string[i:i + 8]
            chunk_bytes = [ord(c) for c in chunk]
            msg.dlc = len(chunk_bytes)
            msg.data[:len(chunk_bytes)] = chunk_bytes
            try:
                self.bus.send(msg)
            except:
                time.sleep(0.001)
                self.bus.send(msg)

    def UserLogin(self, username: str, password: str):
        reader = can.BufferedReader()
        notifier = Notifier(self.bus, [reader])
        userData = f'username={username}&password={password}'
        userDataLength = len(userData)
        msg = can.Message(arbitration_id=LOGIN_ID, is_extended_id=False, dlc=2,
                          data=[(0xFF & userDataLength), (0xFF00 & userDataLength) >> 8])
        self.bus.send(msg)
        msg.arbitration_id = DATA_ID
        msg.dlc = 8
        self.sendStr(self.bus, userData, DATA_ID)

        response_msg = reader.get_message(timeout=15)
        if response_msg is None:
            print("Login response timeout")
            notifier.stop()
            return None, "Invalid"
        statusCode = response_msg.data[0] | (response_msg.data[1] << 8)
        if statusCode == 200:
            date = f'{chr(response_msg.data[2])}{chr(response_msg.data[3])}-{chr(response_msg.data[4])}{chr(response_msg.data[5])}-20{chr(response_msg.data[6])}{chr(response_msg.data[7])}'
            notifier.stop()
            return statusCode, date
        notifier.stop()
        return statusCode, "Invalid"

    def UserSignup(self, username: str, password: str, phone: str, car_id: int):
        reader = can.BufferedReader()
        notifier = Notifier(self.bus, [reader])

        userData = f'{{"username": "{username}", "password": "{password}", "phone": "{phone}", "car_id": {car_id}}}'
        print(userData)
        userDataLength = len(userData)
        msg = can.Message(arbitration_id=SIGNUP_ID, is_extended_id=False, dlc=2,
                          data=[(0xFF & userDataLength), (0xFF00 & userDataLength) >> 8])
        self.bus.send(msg)
        msg.arbitration_id = DATA_ID
        msg.dlc = 8
        self.sendStr(self.bus, userData, DATA_ID)

        response_msg = reader.get_message(timeout=15)
        if response_msg is None:
            notifier.stop()
            print("Signup response timeout")
            return None
        statusCode = response_msg.data[0] | (response_msg.data[1] << 8)
        notifier.stop()
        return statusCode

    def DownloadUpdate(self, firmware_id: str):
        reader = can.BufferedReader()
        notifier = Notifier(self.bus, [reader])

        self.sendStr(self.bus, firmware_id, UPDATE_ID)
        msg_statues = reader.get_message(timeout=80)
        if msg_statues is None:
            print("no status msg received")
            notifier.stop()
            return None, None

        status = msg_statues.data[0] | msg_statues.data[1] << 8
        print(f'status code = {status}')
        if status != 200:
            notifier.stop()
            return status, None
        firmwareSize = msg_statues.data[2] | msg_statues.data[3] << 8
        print(f'firmware size = {firmwareSize}')
        progressThread = Thread(target=self.RecvProgressThread, args=(self.bus, firmwareSize,))
        progressThread.start()
        notifier.stop()
        print("Done")
        return status, progressThread

    def RecvProgressThread(self, firmware_size: int):
        reader = can.BufferedReader()
        notifier = Notifier(self.bus, [reader])

        progress_msg = reader.get_message(timeout=15)
        if progress_msg is None:
            print("receiveing progress Timeout!")
            return
        progress = progress_msg.data[0] | progress_msg.data[1] << 8
        while progress < firmware_size:
            progress_msg = reader.get_message(timeout=15)
            if progress_msg is None:
                notifier.stop()
                print("receiveing progress Timeout!")
                return
            progress = progress_msg.data[0] | progress_msg.data[1] << 8
            print("Progress = " + str(progress))
        print("RecvProgressThread Terminate!")
        firmwareSize = 0
        notifier.stop()

    def GetECU_Diagnostic(self, ecu_id: int):
        reader = can.BufferedReader()
        notifier = Notifier(self.bus, [reader])
        msg = can.Message(arbitration_id=ECU_DIAGNOSTIC_LOG_ID, is_extended_id=False, dlc=2,
                          data=[0xff & ecu_id, 0xff & (ecu_id >> 8)])
        self.bus.send(msg)
        fileSize_msg = reader.get_message(timeout=15)
        if fileSize_msg is None:
            print("Timeout, Failed to receive DiagFile Size!")
            return None
        DiagFileSize = fileSize_msg.data[0] | fileSize_msg.data[1] << 8
        print("DiagFileSize = " + str(DiagFileSize))
        DiagFile_byte = b''
        while True:
            message = reader.get_message(timeout=15)
            if message == None:
                print("Timeout while receiving DiagFile, received Data Size =" + str(len(DiagFile_byte)) + "/" + str(
                    DiagFileSize))
                notifier.stop()
                return None
            DiagFile_byte += message.data
            if len(DiagFile_byte) >= DiagFileSize:
                break
        DiagFile = DiagFile_byte.decode()
        notifier.stop()
        return DiagFile

    def SendDiagnostic(self, car_id: int, ecu_id: int, Diagfile: str):
        reader = can.BufferedReader()
        notifier = Notifier(self.bus, [reader])
        msg = can.Message(arbitration_id=DIAGNOSTIC_RQ_ID, is_extended_id=False, dlc=2,
                          data=[0xff & len(Diagfile), 0xff & (len(Diagfile) >> 8)])
        try:
            self.bus.send(msg)
        except:
            time.sleep(0.001)
            self.bus.send(msg)
        self.sendStr(self.bus, Diagfile, DATA_ID)
        metaData = f'car_id={car_id}&ecu_id={ecu_id}'
        msg = can.Message(arbitration_id=DATA_ID, is_extended_id=False, dlc=2,
                          data=[0xff & len(metaData), 0xff & (len(metaData) >> 8)])

        try:
            self.bus.send(msg)
        except:
            time.sleep(0.001)
            self.bus.send(msg)
        self.sendStr(self.bus, metaData, DATA_ID)
        Status_msg = reader.get_message(timeout=15)
        if Status_msg == None:
            print("Timeout, Diagnostic Request!")
            notifier.stop()
            return None

        notifier.stop()
        return Status_msg.data[0] | Status_msg.data[1] << 8


if __name__ == '__main__':
    main()
