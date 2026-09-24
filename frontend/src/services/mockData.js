const mockResults = {
  contract_name: "sample_contract.pdf",

  risk_score: 78,

  risk_level: "HIGH",

  entities: [
    {
      label: "PARTY",
      value: "Company A / Company B",
    },
    {
      label: "DATE",
      value: "November 20, 2019",
    },
    {
      label: "JURISDICTION",
      value: "Delaware",
    },
    {
      label: "CONTRACT TYPE",
      value: "Commercial Agreement",
    },
  ],

  clauses: [
    {
      name: "Termination",
      status: "High Risk",
      confidence: 0.91,
      description:
        "Termination conditions and notice requirements require review.",
    },

    {
      name: "Confidentiality",
      status: "Detected",
      confidence: 0.96,
      description:
        "Confidentiality obligations are present in the agreement.",
    },

    {
      name: "Indemnification",
      status: "Medium Risk",
      confidence: 0.87,
      description:
        "Indemnification obligations may create additional liability exposure.",
    },

    {
      name: "Intellectual Property",
      status: "High Risk",
      confidence: 0.89,
      description:
        "Ownership and assignment provisions should be reviewed carefully.",
    },

    {
      name: "Auto-Renewal",
      status: "Review",
      confidence: 0.82,
      description:
        "Potential renewal obligations require manual verification.",
    },
  ],

  findings: [
    {
      level: "HIGH",
      title: "Termination provision",
      description:
        "Review termination conditions and notice requirements.",
    },

    {
      level: "HIGH",
      title: "Intellectual property ownership",
      description:
        "Review assignment and ownership obligations.",
    },

    {
      level: "MEDIUM",
      title: "Indemnification obligation",
      description:
        "Potential liability exposure should be reviewed.",
    },
  ],
};

export default mockResults;