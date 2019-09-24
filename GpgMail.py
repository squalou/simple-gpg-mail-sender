# MIT License
#
# Copyright (c) [2019] [squalou.jenkins@gmail.com]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import tkinter as tk
from tkinter.filedialog import askopenfilename
from tkinter import messagebox
import os
import gnupg
from email.mime.multipart import MIMEMultipart, MIMEBase
from email.mime.text import MIMEText
from base64 import encodebytes
import random
import json
import smtplib
import logging
import logging.handlers

# customize these 2 lines for emails *recipient*'s gpg public key id
GPG_KEY_ID = "0x1254798657465446"
GPG_DEST_EMAIL = "someone@nowhere.com"

APP_NAME = "secure mail sender"
WORKDIR = os.path.dirname(os.path.realpath(__file__))
GPG_LOCAL_WORKDIR = WORKDIR + os.path.sep + "_gpg"
SEED_FILE = GPG_LOCAL_WORKDIR + os.path.sep + "local-seed"

def log_setup():
    log_handler = logging.handlers.RotatingFileHandler('secure-mail.log', maxBytes=1024*1024, backupCount=2)
    formatter = logging.Formatter('%(asctime)s [%(process)d]:[%(levelname)s]: %(message)s')
    log_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
    logging.critical("loglevels : {}=INFO, {}=DEBUG, {}=CRITICAL".format(logging.INFO, logging.DEBUG, logging.CRITICAL))


class LabeledEntry(tk.Frame):
    def __init__(self, parent, *args, **kargs):
        text = kargs.pop("text", "")
        default = kargs.pop("default", "")
        l_width = kargs.pop("l_width", 8)
        e_width = kargs.pop("e_width", 50)

        tk.Frame.__init__(self, parent)
        self.label = tk.Label(self, text=text, justify=tk.LEFT, width=l_width)
        self.label.grid(sticky=tk.W, column=0, row=0)
        self.entry = tk.Entry(self, *args, **kargs, width=e_width)
        if default:
            self.entry.insert(tk.END, default)
        self.entry.grid(sticky=tk.E, column=1, row=0)

    def set_focus(self):
        self.entry.focus()

    def get_text(self):
        return self.entry.get()


class TimedMessage:
    def __init__(self, message, delay_millis=0):
        self.top = tk.Toplevel()
        self.top.geometry("300x50")
        self.top.title(APP_NAME)
        tk.Message(self.top, text=message, padx=4, pady=4, justify=tk.CENTER, width=290).pack(fill=tk.X)
        self.top.attributes('-topmost', True)
        logging.debug(message)
        if delay_millis > 0:
            self.top.after(delay_millis, self.top.destroy)

    def destroy(self):
        self.top.destroy()


class ConfigBean:
    def __init__(self):
        self.sender = "someone@email.com"
        self.smtp_server = None
        self.smtp_user = None
        self.smtp_port = None
        self.smtp_password = None
        self.log_level = logging.INFO


class ConfigHandler:
    def __init__(self):
        self.config_file = WORKDIR+os.path.sep+"secure-mail.conf"
        self.cfg_window = None
        self.config_bean = ConfigBean()
        self.pass_mask = "************"
        self.server = None
        self.port = None
        self.user = None
        self.password = None
        self.sender = None
        self.seed = self._init_seed()

    def get_decrypted_smtp_passwd(self):
        return self._decrypt(self.config_bean.smtp_password)

    def get_smtp_user(self):
        return self.config_bean.smtp_user

    def get_smtp_server(self):
        return self.config_bean.smtp_server

    def get_smtp_port(self):
        return self.config_bean.smtp_port

    def get_sender(self):
        return self.config_bean.sender

    def get_log_level(self):
        return self.config_bean.log_level

    def read(self):
        if os.path.isfile(self.config_file):
            with open(self.config_file, "r") as file:
                data = json.load(file)
                self.config_bean.smtp_server = data.get('smtp_server', "")
                self.config_bean.smtp_port = data.get('smtp_port', "")
                self.config_bean.smtp_user = data.get('smtp_user', "")
                self.config_bean.smtp_password = data.get('smtp_password', self._encrypt(self.pass_mask))
                self.config_bean.sender = data.get('sender', "")
                self.config_bean.log_level = data.get('log_level', logging.INFO)
                logging.getLogger().setLevel(self.get_log_level())
                logging.critical("current log level : {}".format(self.get_log_level()))

        else:
            self.config()

    def store(self):
        if self.password.get_text() != self.pass_mask:
            self.config_bean.smtp_password = self._encrypt(self.password.get_text())
        self.config_bean.smtp_server = self.server.get_text()
        self.config_bean.smtp_port = self.port.get_text()
        self.config_bean.smtp_user = self.user.get_text()
        self.config_bean.sender = self.sender.get_text()
        a = json.dumps(self.config_bean, default=lambda o: o.__dict__, sort_keys=True, indent=4)
        logging.debug(a)
        with open(self.config_file, "w") as file:
            file.write(a)
        logging.info("stored configuration to {}".format(self.config_file))
        self.read()
        self.cfg_window.destroy()

    def _init_seed(self):
        if os.path.isfile(SEED_FILE):
            with open(SEED_FILE, "r") as file:
                seed = file.readline()
        else:
            logging.info("initializing local crypto seed")
            chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            seed = ""
            for _ in range(50):
                seed = "{}{}".format(seed, random.choice(chars))
            with open(SEED_FILE, "w") as file:
                file.write(seed)
            if os.path.isfile(self.config_file):
                logging.info("removing previous configuration file {}".format(self.config_file))
                os.remove(self.config_file)
        return seed

    def _encrypt(self, string):
        if string is None:
            return None
        int_list = []
        password_len = len(self.seed)
        for cnt, sym in enumerate(string):
            password_sym = self.seed[cnt % password_len]
            int_list.append(ord(sym)-ord(password_sym))
        return int_list

    def _decrypt(self, int_list):
        if int_list is None or len(int_list)<1:
            return None
        output_string = ""
        password_len = len(self.seed)
        for cnt, numb in enumerate(int_list):
            password_sym = self.seed[cnt % password_len]
            output_string += chr(numb+ord(password_sym))
        return output_string

    def config(self):
        self.cfg_window = tk.Toplevel()
        self.cfg_window.title("smtp config")
        self.server = LabeledEntry(self.cfg_window, text="smtp server : ", default=self.get_smtp_server(), l_width="18")
        self.server.pack()
        self.port = LabeledEntry(self.cfg_window, text="smtp port : ", default=self.get_smtp_port(), l_width="18")
        self.port.pack()
        self.user = LabeledEntry(self.cfg_window, text="smtp login : ", default=self.get_smtp_user(), l_width="18")
        self.user.pack()
        self.password = LabeledEntry(self.cfg_window, text="smtp password : ", default=self.pass_mask, l_width="18")
        self.password.pack()
        self.sender = LabeledEntry(self.cfg_window, text="email expéditeur : ", default=self.get_sender(), l_width="18")
        self.sender.pack()
        button_quit = tk.Button(self.cfg_window, text="annuler", command=self.cfg_window.destroy)
        button_quit.pack(side=tk.BOTTOM, fill=tk.X)
        button_save = tk.Button(self.cfg_window, text="sauvegarder configuration", command=self.store)
        button_save.pack(side=tk.BOTTOM, fill=tk.X)
        self.cfg_window.attributes('-topmost', True)


class Root(tk.Tk):
    def __init__(self):
        super().__init__()
        # DATA
        self.destination_email = GPG_DEST_EMAIL
        self.filename = None
        self.config_handler = None
        self._setup()

        # GUI
        self.root_window = self.winfo_toplevel()
        self.title(APP_NAME)
        self.config_button = tk.Button(self, text="configuration", command=self.config_handler.config)
        self.config_button.pack(side=tk.TOP, fill=tk.X)
        self.label = tk.Label(self, text="À : {}".format(self.destination_email), padx=5, pady=5)
        self.label.pack()
        self.subject = LabeledEntry(self, text="Objet : ")
        self.subject.pack()
        self.file_label = tk.Label(self, text="File :", padx=5, pady=5)
        self.file_label.pack()
        self.text = tk.Text(self.root_window, height=10)
        self.text.pack()
        self.text.insert(tk.END, "hello \n\n<Ce texte ne sera pas chiffré ! ne pas écrire de données sensibles>")
        self.send_button = tk.Button(self.root_window, text="envoyer", command=self.send_email, state=tk.DISABLED)
        self.send_button.pack(side=tk.BOTTOM, fill=tk.X)
        self.add_document_button = tk.Button(self.root_window, text="ajouter fichier", command=self.add_document)
        self.add_document_button.pack(side=tk.BOTTOM, fill=tk.X)
        self.add_document_button.focus()

    def _setup(self):
        if not os.path.isdir(GPG_LOCAL_WORKDIR):
            os.makedirs(GPG_LOCAL_WORKDIR, 0o0700)
        self.config_handler = ConfigHandler()
        self.config_handler.read()

    def add_document(self):
        logging.debug("adding doc")
        f = askopenfilename()
        logging.debug(f)
        if f is not None and len(f) > 0 and os.path.isfile(f):
            self.filename = f
            self.send_button.config(state=tk.NORMAL)
            self.file_label.config(text="File : {}".format(self.filename))
            self.subject.set_focus()
        else:
            self.send_button.config(state=tk.DISABLED)

    def send_email(self):
        logging.info("sending email")
        logging.debug("To {}".format(self.destination_email))
        logging.debug("Object {}".format(self.subject.get_text()))
        logging.debug("Email content \n{}".format(self.text.get(1.0, "end-1c")))
        attachment = self.gpg_encrypt()

        msg = MIMEMultipart()

        msg['From'] = self.config_handler.get_sender()
        msg['To'] = self.destination_email
        msg['Subject'] = self.subject.get_text()
        msg.attach(MIMEText(self.text.get(1.0, "end-1c"), 'plain'))

        a = messagebox.askyesno(APP_NAME, "Confirmer envoi de l'e-mail ?")

        if a:
            fp = open(attachment, 'rb')
            part = MIMEBase('application', "octet-stream")
            part.set_payload(encodebytes(fp.read()).decode())
            fp.close()
            os.remove(attachment)
            part.add_header('Content-Transfer-Encoding', 'base64')
            part.add_header('Content-Disposition', 'attachment; filename="%s"' % attachment)
            msg.attach(part)

            try:
                server = smtplib.SMTP_SSL(self.config_handler.get_smtp_server(), self.config_handler.get_smtp_port())
                server.ehlo()
                server.login(self.config_handler.get_smtp_user(), self.config_handler.get_decrypted_smtp_passwd())
                errs = server.sendmail(msg['From'], [msg['To']], msg.as_string())
                if errs != {}:
                    logging.error("mail not sent to some recipients")
                    logging.error(errs)
                messagebox.showinfo(APP_NAME, "E-mail envoyé ! OK pour quitter.")
            except Exception as e:
                logging.error(e)
                messagebox.showerror(APP_NAME, e)

            self.root_window.destroy()

    def gpg_encrypt(self):
        gpg = gnupg.GPG(gnupghome=GPG_LOCAL_WORKDIR)
        self._gpg_import_keys(gpg)
        out_file = "{}{}secure-{}.gpg".format(GPG_LOCAL_WORKDIR, os.path.sep, random.randint(10000000, 99999999))
        ms = "chiffrement de la pièce jointe ..."
        logging.info(ms)
        m = TimedMessage(ms)

        with open(self.filename, 'rb') as f:
            status = gpg.encrypt_file(
                f, recipients=[self.destination_email],
                always_trust=True,
                output=out_file)

        logging.info('crypt status ok: {}'.format(status.ok))

        m.destroy()
        if status.ok:
            return out_file
        else:
            logging.error('crypt status: {}'.format(status.status))
            logging.error('crypt stderr: {}'.format(status.stderr))
            messagebox.showerror(APP_NAME, status.stderr)
            raise RuntimeError("Encryption error\n{}".format(status.stderr))

    @staticmethod
    def _gpg_import_keys(gpg):
        m = TimedMessage("récupération de la clef de chiffrement ...")
        keyservers = ["ha.pool.sks-keyservers.net"] # "keys.openpgp.org"

        for k in keyservers:
            import_result = gpg.recv_keys(k, GPG_KEY_ID)
            logging.debug(import_result.results)

        public_keys = gpg.list_keys()
        logging.info("public keys :\n{}".format(public_keys))
        m.destroy()


if __name__ == "__main__":
    log_setup()
    root = Root()
    root.mainloop()
