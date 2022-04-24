# get-comics
Download comics programmatically and assemble them as attachments to one email.

## Command-line options

* `-c CONFIG.JSON` required config file 
  (see `example.config.json` to get started)
* `-v` verbose options for debugging

## Config file format

JSON object with the following keys
* `comics`
  * list of comic specifications; each is a two-item list
    * for each comic, the first item is the comic 
      name copied exactly from the URL, and 
    * the second is one of the supported site types, currently
      `gocomics`, `dilbert`, or `kingdom`
* `mail_to`: list of e-mail addresses
* `mail_from`: one e-mail address
