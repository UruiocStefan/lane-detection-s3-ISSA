import socket
import select
import pickle
import datetime

from typing import *


class ObjectSocketParams:
    """Contine constantele folosite de ObjectSenderSocket si ObjectReceiverSocket.

    Attributes:
        OBJECT_HEADER_SIZE_BYTES (int): numarul de octeti folositi pentru a trimite,
            inaintea fiecarui obiect, dimensiunea (in octeti) a acelui obiect.
            Receiverul citeste mai intai acesti octeti ca sa stie cati octeti
            mai are de asteptat pentru obiectul propriu-zis.
        DEFAULT_TIMEOUT_S (int): numarul de secunde de asteptare implicit,
            folosit atunci cand se asteapta date noi pe socket, inainte de a
            considera ca a trecut timpul alocat (timeout).
        CHUNK_SIZE_BYTES (int): dimensiunea maxima (in octeti) a unei singure
            bucati de date citite dintr-o data de pe socket. Datele mari sunt
            citite in mai multe bucati de aceasta dimensiune, nu dintr-o
            singura data.
    """
    OBJECT_HEADER_SIZE_BYTES = 4
    DEFAULT_TIMEOUT_S = 1
    CHUNK_SIZE_BYTES = 1024


class ObjectSenderSocket:
    """Socket care trimite obiecte Python catre un ObjectReceiverSocket.

    Aceasta clasa creeaza un socket TCP, asteapta ca un receiver sa se
    conecteze la el, si apoi permite trimiterea de obiecte Python arbitrare
    (liste, tupluri, array-uri Numpy, etc.) catre acel receiver, folosind
    pickle pentru serializare.

    Attributes:
        ip (str): adresa IP pe care asculta acest socket.
        port (int): portul pe care asculta acest socket.
        sock (socket.socket): socket-ul principal, folosit pentru a asculta
            conexiuni.
        conn (socket.socket): socket-ul conexiunii curente cu receiverul,
            folosit efectiv pentru a trimite date. Este None pana cand un
            receiver se conecteaza.
        print_when_awaiting_receiver (bool): daca True, se afiseaza mesaje in
            consola cand se asteapta conectarea unui receiver.
        print_when_sending_object (bool): daca True, se afiseaza un mesaj in
            consola de fiecare data cand se trimite un obiect.
    """

    ip: str
    port: int
    sock: socket.socket
    conn: socket.socket
    print_when_awaiting_receiver: bool
    print_when_sending_object: bool

    def __init__(self, ip: str, port: int,
                 print_when_awaiting_receiver: bool = False,
                 print_when_sending_object: bool = False):
        """Creeaza socket-ul si asteapta conectarea unui receiver.

        Args:
            ip (str): adresa IP pe care va asculta acest socket (de exemplu
                '127.0.0.1' pentru conexiuni doar de pe acest calculator).
            port (int): portul pe care va asculta acest socket.
            print_when_awaiting_receiver (bool, optional): daca True, se
                afiseaza mesaje in consola in timp ce se asteapta conectarea
                unui receiver. Daca nu este specificat, valoarea implicita
                este False, deci nu se afiseaza niciun mesaj.
            print_when_sending_object (bool, optional): daca True, se
                afiseaza un mesaj in consola de fiecare data cand se trimite
                un obiect. Daca nu este specificat, valoarea implicita este
                False, deci nu se afiseaza niciun mesaj.

        Returns:
            None
        """
        self.ip = ip
        self.port = port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.ip, self.port))
        self.conn = None

        self.print_when_awaiting_receiver = print_when_awaiting_receiver
        self.print_when_sending_object = print_when_sending_object

        self.await_receiver_conection()

    def await_receiver_conection(self):
        """Asteapta (blocant) ca un ObjectReceiverSocket sa se conecteze.

        Pune socket-ul in modul de ascultare si blocheaza executia pana cand
        un receiver se conecteaza. Dupa ce conexiunea este stabilita,
        rezultatul este salvat in atributul self.conn, folosit ulterior de
        send_object() pentru a trimite efectiv datele.

        Daca self.print_when_awaiting_receiver este True, se afiseaza mesaje
        in consola inainte si dupa ce conexiunea este stabilita.

        Args:
            Nu are parametri (in afara de self).

        Returns:
            None
        """

        if self.print_when_awaiting_receiver:
            print(f'[{datetime.datetime.now()}][ObjectSenderSocket/{self.ip}:{self.port}] awaiting receiver connection...')

        self.sock.listen(1)
        self.conn, _ = self.sock.accept()

        if self.print_when_awaiting_receiver:
            print(f'[{datetime.datetime.now()}][ObjectSenderSocket/{self.ip}:{self.port}] receiver connected')

    def close(self):
        """Inchide conexiunea curenta cu receiverul.

        Dupa apelarea acestei metode, self.conn devine None, deci
        is_connected() va returna False si send_object() nu va mai putea fi
        folosit pana la o noua conectare.

        Args:
            Nu are parametri (in afara de self).

        Returns:
            None
        """
        self.conn.close()
        self.conn = None

    def is_connected(self) -> bool:
        """Verifica daca exista in acest moment o conexiune activa cu un receiver.

        Args:
            Nu are parametri (in afara de self).

        Returns:
            bool: True daca exista o conexiune activa (self.conn nu este
            None), False in caz contrar (de exemplu inainte de conectare sau
            dupa apelarea close()).
        """
        return self.conn is not None

    def send_object(self, obj: Any):
        """Serializeaza si trimite un obiect Python catre receiverul conectat.

        Obiectul este mai intai serializat cu pickle, apoi este trimisa
        dimensiunea (in octeti) a datelor serializate (pe un numar fix de
        octeti, dat de ObjectSocketParams.OBJECT_HEADER_SIZE_BYTES), si in
        final sunt trimise datele propriu-zise. Acest "antet" cu dimensiunea
        datelor este ceea ce permite receiverului (in recv_object()) sa stie
        exact cati octeti trebuie sa citeasca pentru a reconstitui obiectul.

        Args:
            obj (Any): orice obiect Python care poate fi serializat cu
                pickle (numere, string-uri, liste, tupluri, dictionare,
                array-uri Numpy, tupluri continand cadre video, etc.).

        Returns:
            None

        Raises:
            AttributeError: daca se apeleaza inainte de a exista o conexiune
                activa (self.conn este None).
        """
        data = pickle.dumps(obj)
        data_size = len(data)
        data_size_encoded = data_size.to_bytes(ObjectSocketParams.OBJECT_HEADER_SIZE_BYTES, 'little')
        self.conn.sendall(data_size_encoded)
        self.conn.sendall(data)
        if self.print_when_sending_object:
            print(f'[{datetime.datetime.now()}][ObjectSenderSocket/{self.ip}:{self.port}] Sent object of size {data_size} bytes.')



class ObjectReceiverSocket:
    """Socket care primeste obiecte Python trimise de un ObjectSenderSocket.

    Aceasta clasa se conecteaza activ la un ObjectSenderSocket aflat deja in
    asteptare, si apoi permite primirea de obiecte Python arbitrare, trimise
    de acesta, folosind pickle pentru deserializare.

    Attributes:
        ip (str): adresa IP a senderului la care se conecteaza.
        port (int): portul senderului la care se conecteaza.
        conn (socket.socket): socket-ul conexiunii cu senderul, folosit
            pentru a primi date.
        print_when_connecting_to_sender (bool): daca True, se afiseaza
            mesaje in consola in timp ce se incearca conectarea la sender.
        print_when_receiving_object (bool): daca True, se afiseaza un mesaj
            in consola de fiecare data cand se primeste un obiect.
    """

    ip: str
    port: int
    conn: socket.socket
    print_when_connecting_to_sender: bool
    print_when_receiving_object: bool

    def __init__(self, ip: str, port: int,
                 print_when_connecting_to_sender: bool = False,
                 print_when_receiving_object: bool = False):
        """Creeaza receiverul si se conecteaza imediat la sender.

        Args:
            ip (str): adresa IP a senderului la care se va conecta (trebuie
                sa fie aceeasi adresa folosita de ObjectSenderSocket).
            port (int): portul senderului la care se va conecta (trebuie sa
                fie acelasi port folosit de ObjectSenderSocket).
            print_when_connecting_to_sender (bool, optional): daca True, se
                afiseaza mesaje in consola in timpul conectarii la sender.
                Daca nu este specificat, valoarea implicita este False, deci
                nu se afiseaza niciun mesaj.
            print_when_receiving_object (bool, optional): daca True, se
                afiseaza un mesaj in consola de fiecare data cand se
                primeste un obiect. Daca nu este specificat, valoarea
                implicita este False, deci nu se afiseaza niciun mesaj.

        Returns:
            None
        """
        self.ip = ip
        self.port = port
        self.print_when_connecting_to_sender = print_when_connecting_to_sender
        self.print_when_receiving_object = print_when_receiving_object

        self.connect_to_sender()

    def connect_to_sender(self):
        """Se conecteaza (blocant) la ObjectSenderSocket-ul aflat in asteptare.

        Creeaza un nou socket TCP si incearca sa se conecteze la adresa/
        portul specificate la ip/port. Rezultatul conexiunii este salvat in
        self.conn, folosit ulterior de recv_object() pentru a primi date.

        Daca self.print_when_connecting_to_sender este True, se afiseaza
        mesaje in consola inainte si dupa ce conexiunea este stabilita.

        Args:
            Nu are parametri (in afara de self).

        Returns:
            None
        """

        if self.print_when_connecting_to_sender:
            print(f'[{datetime.datetime.now()}][ObjectReceiverSocket/{self.ip}:{self.port}] connecting to sender...')

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((self.ip, self.port))

        if self.print_when_connecting_to_sender:
            print(f'[{datetime.datetime.now()}][ObjectReceiverSocket/{self.ip}:{self.port}] connected to sender')

    def close(self):
        """Inchide conexiunea curenta cu senderul.

        Dupa apelarea acestei metode, self.conn devine None, deci
        is_connected() va returna False si recv_object() nu va mai putea fi
        folosit pana la o noua conectare.

        Args:
            Nu are parametri (in afara de self).

        Returns:
            None
        """
        self.conn.close()
        self.conn = None

    def is_connected(self) -> bool:
        """Verifica daca exista in acest moment o conexiune activa cu senderul.

        Args:
            Nu are parametri (in afara de self).

        Returns:
            bool: True daca exista o conexiune activa (self.conn nu este
            None), False in caz contrar (de exemplu inainte de conectare sau
            dupa apelarea close()).
        """
        return self.conn is not None

    def recv_object(self) -> Any:
        """Primeste si reconstituie urmatorul obiect trimis de sender.

        Citeste mai intai antetul cu dimensiunea obiectului (vezi
        _recv_object_size()), apoi citeste exact atatia octeti (vezi
        _recv_all()), si in final deserializeaza acei octeti cu pickle
        pentru a obtine inapoi obiectul Python original trimis de sender.

        Args:
            Nu are parametri (in afara de self).

        Returns:
            Any: obiectul Python trimis de sender (poate fi orice tip de
            obiect serializabil cu pickle: numere, string-uri, liste,
            tupluri, dictionare, array-uri Numpy, etc.).

        Raises:
            socket.error: daca se depaseste timpul de asteptare
                (DEFAULT_TIMEOUT_S) fara sa se primeasca toti octetii
                asteptati.
        """
        obj_size_bytes = self._recv_object_size()
        data = self._recv_all(obj_size_bytes)
        obj = pickle.loads(data)
        if self.print_when_receiving_object:
            print(f'[{datetime.datetime.now()}][ObjectReceiverSocket/{self.ip}:{self.port}] Received object of size {obj_size_bytes} bytes.')
        return obj

    def _recv_with_timeout(self, n_bytes: int, timeout_s: float = ObjectSocketParams.DEFAULT_TIMEOUT_S) -> Optional[bytes]:
        """Incearca sa primeasca pana la n_bytes octeti, cu limita de timp.

        Foloseste select.select() ca sa astepte pana la timeout_s secunde ca
        socket-ul sa aiba date disponibile de citit. Daca datele devin
        disponibile inainte de timeout, sunt citite si returnate (pot fi mai
        putini octeti decat n_bytes, socket-urile TCP pot returna date in
        bucati mai mici decat cele cerute). Daca timpul alocat trece fara ca
        date sa devina disponibile, se returneaza None.

        Args:
            n_bytes (int): numarul maxim de octeti care se incearca a fi
                cititi intr-un singur apel.
            timeout_s (float, optional): numarul de secunde de asteptare
                inainte de a considera ca a trecut timpul alocat. Daca nu
                este specificat, se foloseste valoarea implicita
                ObjectSocketParams.DEFAULT_TIMEOUT_S (1 secunda).

        Returns:
            Optional[bytes]: octetii primiti (pot fi mai putini decat
            n_bytes), sau None daca s-a depasit timpul alocat fara sa se
            primeasca nicio data noua.
        """
        rlist, _1, _2 = select.select([self.conn], [], [], timeout_s)
        if rlist:
            data = self.conn.recv(n_bytes)
            return data
        else:
            return None

    def _recv_all(self, n_bytes: int, timeout_s: float = ObjectSocketParams.DEFAULT_TIMEOUT_S) -> bytes:
        """Primeste exact n_bytes octeti, apeland _recv_with_timeout() in bucla.

        Deoarece un singur apel de recv() poate returna mai putini octeti
        decat s-a cerut, aceasta metoda continua sa apeleze
        _recv_with_timeout() in bucla, adunand bucatile primite, pana cand
        s-au primit in total exact n_bytes octeti.

        Args:
            n_bytes (int): numarul total de octeti care trebuie primiti.
            timeout_s (float, optional): numarul de secunde de asteptare
                pentru fiecare incercare de citire, inainte de a considera
                ca a trecut timpul alocat. Daca nu este specificat, se
                foloseste valoarea implicita
                ObjectSocketParams.DEFAULT_TIMEOUT_S (1 secunda).

        Returns:
            bytes: toti cei n_bytes octeti primiti, concatenati intr-un
            singur obiect bytes.

        Raises:
            socket.error: daca la un moment dat trece timpul alocat
                (timeout_s) fara sa se mai primeasca nicio data noua,
                inainte de a se aduna toti cei n_bytes octeti asteptati.
        """
        data = []
        left_to_recv = n_bytes
        while left_to_recv > 0:
            desired_chunk_size = min(ObjectSocketParams.CHUNK_SIZE_BYTES, left_to_recv)
            chunk = self._recv_with_timeout(desired_chunk_size, timeout_s)
            if chunk is not None:
                data += [chunk]
                left_to_recv -= len(chunk)
            else:
                bytes_received = sum(map(len, data))
                raise socket.error(f'Timeout elapsed without any new data being received. '
                                   f'{bytes_received} / {n_bytes} bytes received.')
        data = b''.join(data)
        return data

    def _recv_object_size(self) -> int:
        """Primeste si decodeaza antetul cu dimensiunea urmatorului obiect.

        Citeste exact ObjectSocketParams.OBJECT_HEADER_SIZE_BYTES octeti
        (antetul trimis de send_object() inainte de datele propriu-zise) si
        ii decodeaza ca pe un numar intreg, folosind ordinea de octeti
        'little' (little-endian), aceeasi conventie folosita la trimitere
        in send_object().

        Args:
            Nu are parametri (in afara de self).

        Returns:
            int: dimensiunea (in octeti) a urmatorului obiect ce va fi
            trimis de sender, asa cum a fost codificata in antet.

        Raises:
            socket.error: daca se depaseste timpul de asteptare inainte de
                a se primi toti octetii antetului.
        """
        data = self._recv_all(ObjectSocketParams.OBJECT_HEADER_SIZE_BYTES)
        obj_size_bytes = int.from_bytes(data, 'little')
        return obj_size_bytes