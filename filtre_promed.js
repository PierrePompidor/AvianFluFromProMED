var months = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','April':'04','May':'05','Jun':'06','Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':"12"};

function filtre (datemin, datemax) {
    let data = datemin.split("-");
    let ndatemin = data[0]+data[1]+data[2];
    console.log(ndatemin);
    data = datemax.split("-");
    let ndatemax = data[0]+data[1]+data[2];
    console.log(ndatemax);

    let nevents = [];

    let nbPosts = 0;
    let nbMatchedPosts = 0;
    for (let event of promed) {
        nbPosts++;
        let date = event.event_date;
        const re = /(\d+) (.+) (\d+)/;
        const data = re.exec(date);
        // TODO : April 2023
        if (data != undefined && data.length >= 3) {
            if (months.hasOwnProperty(data[2])) {
                let ndate = data[3]+months[data[2]]+data[1];
                if (ndate >= ndatemin && ndate <= ndatemax) {
                    nbMatchedPosts++;
                    nevents.push(event);                   
                }
                //console.log(ndate);
            }
            else console.log('PB1:', 'data1=', data[1], 'data2=', data[2], 'data3=', data[3]);
        }
        else { console.log("PB: ", date); }
        //console.log(nbMatchedPosts, '/', nbPosts);
    }

    return nevents;
}