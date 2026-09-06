document.addEventListener("DOMContentLoaded", () => {
    if (typeof ipoData !== 'undefined') {
        
        if (ipoData.last_updated) {
            const updatedElement = document.getElementById('last-updated');
            
            // Format the date from YYYY-MM-DD to DD/MM/YYYY
            let displayDate = ipoData.last_updated;
            if (displayDate.includes('-')) {
                const parts = displayDate.split(' '); // Split date and time
                const dateParts = parts[0].split('-'); // Split year, month, day
                // Rearrange to DD/MM/YYYY and add the time back on
                displayDate = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]} ${parts[1]}`;
            }

            updatedElement.textContent = `Last Updated: ${displayDate}`;
            // Add the dynamic color class based on the original date string
            updatedElement.className = getUpdatedColorClass(ipoData.last_updated);
        }

        populateGrowwTable(ipoData.groww_open_ipos);
        populateOtherTable(ipoData.other_mainboard_ipos);
    } else {
        document.querySelector('.container').innerHTML += `
            <p style="color: red; text-align: center;">
                Error: data.js not found. Run the Python script first!
            </p>`;
    }
});

function populateGrowwTable(ipos) {
    const tbody = document.querySelector('#groww-table tbody');
    
    if (ipos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No open IPOs found on Groww.</td></tr>';
        return;
    }

    ipos.forEach(ipo => {
        const startDate = ipo.Starting || "N/A";
        const endDate = ipo.Ending || "N/A";

        const tr = document.createElement('tr');
        // Fix: Added <span> tags around the GMP value
        tr.innerHTML = `
            <td>${ipo.Name}</td>
            <td>${startDate}</td>
            <td>${endDate}</td>
            <td><span class="${getGmpColorClass(ipo.GMP_Percentage)}">${ipo.GMP_Percentage}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function populateOtherTable(ipos) {
    const tbody = document.querySelector('#other-table tbody');
    
    if (ipos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align:center;">No other IPOs found.</td></tr>';
        return;
    }

    ipos.forEach(ipo => {
        const tr = document.createElement('tr');
        // Fix: Added <span> tags around the GMP value
        tr.innerHTML = `
            <td>${ipo.Name}</td>
            <td><span class="${getGmpColorClass(ipo.GMP_Percentage)}">${ipo.GMP_Percentage}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// Utility function to apply CSS colors to the GMP value
function getGmpColorClass(gmpString) {
    if (gmpString === "-%" || gmpString === "N/A" || gmpString === "Not found") {
        return 'gmp-neutral';
    }
    
    const numericValue = parseFloat(gmpString);
    
    if (numericValue > 11) {
        return 'gmp-positive'; 
    } else {
        return 'gmp-negative'; 
    }
}

// Utility function to apply CSS colors to the Last Updated text
function getUpdatedColorClass(updatedString) {
    if (!updatedString) return 'updated-older';

    // Extract just the date part for calculation (e.g., "2026-09-06")
    const datePart = updatedString.split(' ')[0];
    const [year, month, day] = datePart.split('-').map(Number);
    
    // Create date object for the updated day at midnight
    const updatedDate = new Date(year, month - 1, day);
    
    // Create date object for today at midnight to ensure accurate day comparison
    const today = new Date();
    const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    
    // Calculate difference in days
    const diffTime = todayMidnight - updatedDate;
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'updated-today'; // Green (Today)
    } else if (diffDays === 1) {
        return 'updated-yesterday'; // Blue (Yesterday)
    } else {
        return 'updated-older'; // Red (Older)
    }
}