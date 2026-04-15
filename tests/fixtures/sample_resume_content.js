const path = require("path");

const content = {
  name: "Jane Doe",
  contact: [
    "New York, NY | jane@example.com | 555-123-4567",
    "linkedin.com/in/janedoe | github.com/janedoe",
  ],
  summary:
    "Machine Learning Engineer with 3 years of experience building recommendation systems and data pipelines serving 2M+ daily predictions.",
  skills:
    "Python, PyTorch, SQL, AWS SageMaker, Docker, Tableau, dbt, scikit-learn",
  workExperience: [
    {
      company: "Acme Analytics",
      location: "San Francisco, CA",
      title: "Machine Learning Engineer",
      dates: "03/2024 - Present",
      bullets: [
        "Designed and deployed a real-time recommendation model using PyTorch, serving 2M+ daily predictions with sub-50ms latency.",
        "Built an automated A/B testing pipeline that reduced experiment cycle time from 2 weeks to 3 days.",
        "Streamlined feature engineering workflows by implementing a shared feature store, cutting data prep time by 40%.",
        "Optimized model inference costs by migrating to SageMaker serverless endpoints, reducing monthly compute spend by $15K.",
      ],
    },
    {
      company: "GlobalTech Solutions",
      location: "Austin, TX",
      title: "Data Analyst",
      dates: "06/2022 - 02/2024",
      bullets: [
        "Developed a customer segmentation model using k-means clustering on 500K+ records, improving conversion by 18%.",
        "Automated weekly executive reporting with Tableau dashboards, eliminating 8 hours per week of manual Excel work.",
        "Engineered a scalable dbt transformation layer processing 10M+ rows nightly to power the centralized analytics warehouse.",
        "Reduced critical data pipeline failures by 60% by designing and implementing automated quality checks with real-time alerting.",
      ],
    },
    {
      company: "StartupCo",
      location: "Remote",
      title: "Junior Data Scientist",
      dates: "01/2021 - 05/2022",
      bullets: [
        "Built a churn prediction model with scikit-learn that achieved 89% precision on a 200K-customer dataset for proactive retention.",
        "Architected a robust ETL pipeline that ingested structured data from 5 REST APIs into a centralized PostgreSQL warehouse.",
        "Delivered comprehensive monthly cohort analyses to the executive team, identifying a $2.3M revenue retention opportunity across segments.",
      ],
    },
  ],
  selectedProjects: [
    {
      name: "Predictive Maintenance System | Python, FastAPI, Docker",
      dates: "2024",
      bullets: [
        "Engineered an end-to-end predictive maintenance pipeline that processed 1M+ sensor readings daily and achieved 92% recall.",
        "Deployed the model as a FastAPI microservice with Docker, handling 500 requests per minute in production.",
        "Spearheaded end-to-end integration with the existing monitoring stack and alerting system, reducing unplanned downtime by 35%.",
      ],
    },
  ],
  education: {
    school: "State University",
    location: "Austin, TX",
    degree: "BS Computer Science, Minor in Statistics",
    date: "05/2020",
    details: "GPA: 3.7/4.0 | Dean's List",
  },
};

async function main() {
  console.log("Test fixture - not meant to be executed for document generation");
}

main().catch(console.error);
