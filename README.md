
# Bank History
[![GPLv3 License](https://img.shields.io/badge/License-GPL%20v3-yellow.svg)](https://opensource.org/licenses/)

### Keep your bank history organized and archived for consuming via API 

#### What is the purpose of Bank History?
This is a web app I'm coding for myself, the idea is to keep it simple (see the roadmap to understand), the solely reason to exist of Bank History is to create a tool simple enough to collect information off all my financial life (checking accounts, credit cards, investment accounts) and to make it permanent.

It's not meant to be a budget app, an investment tracker, internal transfer between accounts or anyother fancy stuff, it should only do the basics: an account statement, with options to classify, maybe add an attachment and then make it easily backupable and permanent.

It's built in Django to be easy to deploy and the desired output is an SQLite file to be stored in any Cloud Service.




## Roadmap

- Finish the current views (see opened Improvment issues)

- Allow user profile customization (change avatar, passwords, names, locale options)

- Create Rules feature to speed up transaction classification

- Create API feature, to allow user to insert transactions and consume APP data in external tools (Google Sheet, Microsoft Excel, budget app, investment app, etc...)

- Create Export feature to allow permanent archiving of your financial life

- Create a simple dashboard to summarize data in a monthly and yearly view

