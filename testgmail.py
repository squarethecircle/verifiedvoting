from gmail.gmail import GMail
from gmail.message import Message
xmail = GMail('Verified Voting <yaleverifiedvoting@gmail.com>','qyfsewfeepumeaex')
msg = Message('Test Python Gmail Message',to='Soham Sankaran <soham.sankaran@gmail.com>',text='Hello Soham, what is up, dog? Best, Soham')
xmail.send(msg)