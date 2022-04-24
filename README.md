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
      * `gocomics` e.g., https://www.gocomics.com/adamathome/2020/10/08 
        (use `adamathome` as the comic name in the config)
      * `dilbert`, e.g., https://dilbert.com/strip/2020-12-21
        (use `dilbert` as the comic name)
      * `kingdom`, e.g., https://comicskingdom.com/hagar-the-horrible/2022-04-24
        (use `hagar-the-horrible` as the comic name)
* `mail_to`: list of one or more e-mail addresses
* `mail_from`: one e-mail address
