var feedback = document.forms.feedback
feedback.hidden = false 

feedback.addEventListener("submit", function(ev) {
  ev.preventDefault()

  var page = document.location.href
  var data = ev.submitter.getAttribute("data-md-value")

  console.log(page, data) 

  feedback.firstElementChild.disabled = true 

  var note = feedback.querySelector(
    ".md-feedback__note [data-md-value='" + data + "']"
  )
  if (note) {
    note.hidden = false
    
    var issueLink = note.querySelector("a")
    if (issueLink) {
      var currentHref = issueLink.getAttribute("href")
      issueLink.setAttribute("href", currentHref.replace("{url}", encodeURIComponent(page)))
    }
  }
})