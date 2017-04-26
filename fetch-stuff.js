fetch(url, {  
    method: 'POST',  
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    }, 
    body: JSON.stringify(put_blob_here)
})
.then(function (data) {  
  console.log('Request success! The server said: ', data);  
})  
.catch(function (error) {  
  console.log('Verification request failure: ', error);  
});