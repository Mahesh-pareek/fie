- add one edit tag option for a given transaction!
- store the dependencies in the .toml !
- currently summary shows the personal summary only, but itshould show all type of analysis
    like summary -a ( all) else net scope wise, if -p ( or full name) then personal and so on 
- in edit i want to ignore the transcations less then 20rs ( noise and coffee are ignored)


##############

- during edit it iterates over all the transactions, suchha lengthy task
- there should be some way to skip ( if i click enter while editing, it keep the exisiting tags)
- also how do i find the transcation id?


############
the inputs and other commadns can be made more easier to run from the CLI efforts should be put on this!!
- make the CLI simplar and update help functions!!


####################################
- currently it shows the payment  mode ( like UPI/IMPS) we don't want that often, so better if you show the auther as well

- ahh the thing is in the counter party they are storing UPI/IMPS, but clearly that should go in mode not in the counter party!! fix it
- counter party should be used for the name of the user who's involved in the transaction ( clearly/?)


##############################


- summary prints only the personal and full sumamry rn... lets also print the individual breakdown when summary is assked everything is printed
- print less or dedicted only when it's asked~~







######################



TO DO LATEERRRRRRRRRRRRRRRRRR:
- Add an instruction to not add duplicate files/ overlapping files  else the transactions will be doubled

- Should i add a visulaizer???? ( for parsed PDF)
    


- we can also parse time from the raw text... it's pretty easy.. 
-  just look for hh:mm:ss , we don't need to show it , we keep it only for puting it for ease later ( end to end)
- also now is the time we fix the naming issues
- remove all the spaces generate a full string and then extract importnat info from it, like time and correct name ( no weird spacing, cutting)

#################
- fie ls -h 
-fie show <id>


- why do we have fie edit ??


- DAILY AVG SHOULD BE FIXED ON WEBSITE!!
- spending chart has issues, montly and weekly shows the same.. needs to be fixed!!
- now the edited button does not work in the transaction
also deleteing transaction should not be accessible this easily.. they can only be delted after ( what's te standard practice for such system?)
- use that practice only









###############################
- Use a better theme, yellow for dashboard/transaction etx naming ( looks good on black/blaue)
pick a great theme from internet which actually looks good and then make with that!!)
- daily avg ,demove that filed it's misleading 

- also one good feature the updates currently have a clash, if i update something manuallly it should not be obverwrriten by the auto tagging
also give a option (like overwrite all (updates the trsaction which are required to be updated!!)

- also the money out is not correctly showing the expenses of the time ,, it should tell all the expenes ( sum of everything +/- in the personal section!!)
