// 3-stage pipeline hazard controller with stall, forward, and flush.
//
// Pipeline stages: ID (decode) → EX (execute) → WB (writeback).
// Each instruction has source register (rs), destination register (rd),
// an opcode (op), and a valid bit.
//
// Hazard detection:
//   - RAW in EX: id_rs matches ex_rd while ex_valid → can FORWARD from EX result
//   - RAW in WB: id_rs matches wb_rd while wb_valid → can FORWARD from WB result
//   - Load-use: ex_op is LOAD and RAW in EX → must STALL (can't forward yet)
//
// On stall: ID stage holds (re-issues same instruction), EX gets bubble.
// On forward (no stall): ID advances, forward mux selects EX or WB result.
// Forward priority: EX result takes priority over WB when both match.
//
// The stall condition, forward select, and flush logic interact through
// the pipeline valid bits and register specifiers.
module hazard_ctrl(
  input        clk,
  input        reset,
  // ID stage inputs
  input  [1:0] id_rs,
  input  [1:0] id_rd,
  input        id_valid,
  input        id_op,       // 0=ALU, 1=LOAD
  input  [7:0] id_imm,
  // Outputs
  output reg [1:0] ex_rd,
  output reg       ex_valid,
  output reg       ex_op,
  output reg [7:0] ex_result,
  output reg [1:0] wb_rd,
  output reg       wb_valid,
  output reg [7:0] wb_result,
  output reg       stall,
  output reg [7:0] fwd_data
);
  // Hazard detection wires
  wire raw_ex = ex_valid && (ex_rd == id_rd); // HINT: check this line carefully
  wire raw_wb = wb_valid && (wb_rd == id_rs);
  wire load_use = raw_ex && ex_op;               // stall needed for load in EX

  // Forward select: EX priority over WB
  wire do_fwd_ex = raw_ex && !load_use;
  wire do_fwd_wb = raw_wb && !do_fwd_ex;

  initial begin
    ex_rd = 0; ex_valid = 0; ex_op = 0; ex_result = 0;
    wb_rd = 0; wb_valid = 0; wb_result = 0;
    stall = 0; fwd_data = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      ex_rd <= 0; ex_valid <= 0; ex_op <= 0; ex_result <= 0;
      wb_rd <= 0; wb_valid <= 0; wb_result <= 0;
      stall <= 0; fwd_data <= 0;
    end else begin
      // WB stage ← EX stage
      wb_rd     <= ex_rd;
      wb_valid  <= ex_valid;
      wb_result <= ex_result;

      // Stall + forward logic
      stall <= 1'b0;

      // Forward mux
      if (do_fwd_ex)
        fwd_data <= wb_result; // HINT: check this line carefully
      else if (do_fwd_wb)
        fwd_data <= wb_result;
      else
        fwd_data <= id_imm;

      // EX stage ← ID stage (or bubble on stall)
      if (load_use) begin
        ex_valid  <= id_valid;
        ex_rd     <= id_rd;
        ex_op     <= id_op;
        ex_result <= id_imm;
      end else begin
        ex_valid  <= id_valid;
        ex_rd     <= id_rd;
        ex_op     <= id_op;
        ex_result <= do_fwd_ex ? ex_result : (do_fwd_wb ? wb_result : id_imm);
      end
    end
  end

  p_reset:        assert property (@(posedge clk) reset |=> !ex_valid && !wb_valid && !stall);
  p_raw_ex:       assert property (@(posedge clk) !reset && ex_valid && ex_rd == id_rs && id_valid |-> raw_ex);
  p_stall_load:   assert property (@(posedge clk) !reset && load_use |=> stall);
  p_flush:        assert property (@(posedge clk) !reset && load_use |=> !ex_valid);
  p_fwd_ex_val:   assert property (@(posedge clk) !reset && do_fwd_ex |=> fwd_data == $past(ex_result));
  p_fwd_wb_val:   assert property (@(posedge clk) !reset && do_fwd_wb && !do_fwd_ex |=> fwd_data == $past(wb_result));
  p_pipe_advance: assert property (@(posedge clk) !reset && !load_use && id_valid |=> ex_valid && ex_rd == $past(id_rd));
endmodule
