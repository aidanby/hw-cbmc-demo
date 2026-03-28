// 2-stage pipeline with scoreboard bypass (data forwarding).
//
// Each instruction has: rs (source register 0-3), rd (destination 0-3),
// op (0=load immediate, 1=increment reg[rs]+1).
//
// Stage 1: latch inputs, resolve source value via bypass mux.
//   If the previous instruction's destination matches current source (RAW hazard),
//   forward the writeback value instead of reading the register file.
// Stage 2: compute result and write back to register file.
//
// Three bugs corrupt the bypass condition, mux direction, and increment source.
module bypass_pipe(
  input  clk,
  input  reset,
  input  [1:0] rs, rd,
  input  op,
  input  [7:0] imm_in,
  output reg [7:0] result
);
  reg [7:0] regfile [0:3];
  reg [1:0] rs_s1, rd_s1;
  reg       op_s1;
  reg [7:0] imm_s1;
  reg [7:0] src_val;
  reg [7:0] wb_val;
  reg [1:0] rd_wb;
  reg       wb_valid;

  wire bypass = wb_valid && (rd_wb == rd_s1); // HINT: check this line carefully

  initial begin
    rs_s1 = 0; rd_s1 = 0; op_s1 = 0; imm_s1 = 0;
    src_val = 0; wb_val = 0; rd_wb = 0; wb_valid = 0;
    result = 0;
    regfile[0] = 0; regfile[1] = 0; regfile[2] = 0; regfile[3] = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      rs_s1 <= 0; rd_s1 <= 0; op_s1 <= 0; imm_s1 <= 0;
      src_val <= 0; wb_val <= 0; rd_wb <= 0; wb_valid <= 0;
      result <= 0;
      regfile[0] <= 0; regfile[1] <= 0; regfile[2] <= 0; regfile[3] <= 0;
    end else begin
      // Stage 1: latch + resolve source
      rs_s1  <= rs;
      rd_s1  <= rd;
      op_s1  <= op;
      imm_s1 <= imm_in;
      src_val <= bypass ? 8'd0 : regfile[rs_s1];

      // Stage 2: compute + writeback
      if (op_s1 == 1'b0) begin
        wb_val <= imm_s1;                            // load immediate
      end else begin
        wb_val <= imm_s1 + 8'd1;
      end
      rd_wb    <= rs_s1; // HINT: check this line carefully
      wb_valid <= 1'b1;
      result   <= wb_val;

      // Register file write
      if (wb_valid)
        regfile[rd_wb] <= wb_val;
    end
  end

  p_reset:         assert property (@(posedge clk) reset |=> wb_valid == 1'b0);
  p_load:          assert property (@(posedge clk) !reset && op == 1'b0 && imm_in == 8'hAA && rd == 2'd0 ##1 !reset |=> reset || (wb_valid && wb_val == 8'hAA));
  p_bypass_cond:   assert property (@(posedge clk) !reset && wb_valid && rd_wb == rs_s1 |-> bypass == 1'b1);
  p_bypass_val:    assert property (@(posedge clk) !reset && bypass |=> src_val == $past(wb_val));
  p_no_bypass_inc: assert property (@(posedge clk) !reset && !bypass && op_s1 == 1'b1 |=> wb_val == ($past(src_val) + 8'd1));
  p_regfile_wr:    assert property (@(posedge clk) !reset && wb_valid |=> regfile[$past(rd_wb)] == $past(wb_val));
  p_src_reg0:      assert property (@(posedge clk) !reset && !bypass && rs_s1 == 2'd0 |=> src_val == $past(regfile[0]));
  p_wb_dest:       assert property (@(posedge clk) !reset && wb_valid |-> rd_wb == $past(rd_s1));
endmodule
