function convertJsonToTable(json) {
          let table = `
            <table style="width:100%; border-collapse: collapse;">
              <tr>
                <th style="border: 2px solid black; padding: 10px;">Name</th>
                <th style="border: 2px solid black; padding: 10px;">Score</th>
              </tr>
          `;
          console.log('in convertJsonToTable');
          console.log(json);
          console.log(typeof(json));
          json.forEach(match => {
            table += `
              <tr>
                <td style="border: 2px solid black; padding: 10px;">${match.name}</td>
                <td style="border: 2px solid black; padding: 10px;">${match.score}</td>
              </tr>
            `;
          });

          table += "</table>";

          return table;
        }

