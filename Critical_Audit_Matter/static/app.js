async function analyze(){

    const company = document.getElementById("company").value;
    const year = document.getElementById("year").value;
    const output = document.getElementById("output");

    output.textContent = "";

    const response = await fetch("/stream_cam",{
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify({ company, year })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while(true){

        const {done, value} = await reader.read();

        if(done) break;

        output.textContent += decoder.decode(value);
    }
}
